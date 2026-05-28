import json
import logging
import os
import tempfile
import traceback

import anthropic
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

from . import tools
from .models import Conversation, Message, PromptTemplate, TemplateCategory, GeneratedDocument, VoiceNote, MemoryNote
from apps.core.superuser import su_qs, su_get


_SYSTEM_DEFAULT = (
    "You are HiHi — a sharp, concise AI assistant embedded in Andrew's personal business OS at hihilabs.xyz. "
    "Andrew is a solo full-stack developer/architect running FCKRY LLC dba CommunityPlaylist. "
    "He works on Django, Python, PHP, audio tools, hosting, and creative client work. "
    "Be direct, practical, no filler. Markdown is fine.\n\n"
    "You have tools to manage Andrew's business and codebase:\n"
    "— Data: list/create/update projects, tasks, time entries, servers\n"
    "— Search: search_files to grep across the codebase before editing\n"
    "— Files: list_dir, read_file, write_file on the hihilabs source at /workspace/\n"
    "— Git: git_status, git_diff, git_commit to track and commit changes\n"
    "— Deploy: trigger_deploy to push changes live (git pull + reload, or full docker rebuild)\n"
    "— SSH: ssh_run to run commands on any registered server\n"
    "— Django: run_manage for migrate, makemigrations, collectstatic, test, check, etc.\n"
    "— Rebuild: docker_rebuild restarts the local container (60-90s)\n\n"
    "Self-editing + deploy workflow:\n"
    "  1. search_files to locate relevant code\n"
    "  2. read_file to see full context\n"
    "  3. write_file with complete updated content\n"
    "  4. run_manage makemigrations / migrate if models changed\n"
    "  5. git_commit with a clear message\n"
    "  6. trigger_deploy — use cmd='deploy' for .py/.html changes, cmd='full' for static/requirements\n\n"
    "Hot-reload rules — gunicorn --reload is active, so:\n"
    "  • Python files (.py) and templates (.html) → trigger_deploy cmd='deploy' (fast)\n"
    "  • Static files (CSS/JS) or requirements.txt → trigger_deploy cmd='full' (60-90s rebuild)\n"
    "Use tools proactively — when the request involves real data or a code change, do it."
)


def _decode_content(content):
    """Convert stored message content → Claude API format (supports text+image)."""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and 'text' in parsed:
            parts = []
            if parsed.get('text'):
                parts.append({'type': 'text', 'text': parsed['text']})
            for att in parsed.get('attachments', []):
                if att.get('type') == 'image':
                    parts.append({
                        'type': 'image',
                        'source': {'type': 'base64', 'media_type': att['media_type'], 'data': att['data']},
                    })
            return parts if len(parts) > 1 else (parts[0].get('text', '') if parts else '')
    except (json.JSONDecodeError, KeyError, ValueError):
        pass
    return content


def _build_system(user):
    notes = list(MemoryNote.objects.filter(user=user).order_by('key'))
    if notes:
        mem_block = (
            "\n\n## persistent memory\nThese facts persist across all conversations. "
            "Use write_memory to update, delete_memory to remove.\n"
            + "\n".join(f"- **{n.key}**: {n.value}" for n in notes)
        )
    else:
        mem_block = "\n\nNo persistent memories yet. Use write_memory to store facts across conversations."
    return _SYSTEM_DEFAULT + mem_block


def _claude_client():
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# ── Chat ─────────────────────────────────────────────────────────────────────

@login_required
def chat_index(request):
    conversations = su_qs(request.user, Conversation.objects, owner_field='user')
    return render(request, 'claude_ai/chat_index.html', {'conversations': conversations})


@login_required
def chat_new(request):
    conv = Conversation.objects.create(user=request.user)
    return redirect('ai:chat', pk=conv.pk)


@login_required
def chat_detail(request, pk):
    try:
        conv = su_get(Conversation, pk, request.user, owner_field='user')
        messages = conv.messages.all()
        conversations = su_qs(request.user, Conversation.objects, owner_field='user')
        memory_notes = su_qs(request.user, MemoryNote.objects, owner_field='user')
        return render(request, 'claude_ai/chat.html', {
            'conv': conv,
            'messages': messages,
            'conversations': conversations,
            'memory_notes': memory_notes,
        })
    except Exception as e:
        tb = traceback.format_exc()
        logger.error('chat_detail error: %s\n%s', e, tb)
        return HttpResponse(
            f'<h1 style="color:red">Error</h1><pre style="background:#111;color:#0f0;padding:20px;white-space:pre-wrap">{tb}</pre>',
            status=500,
        )


@login_required
@require_POST
def chat_send(request, pk):
    import base64
    conv = su_get(Conversation, pk, request.user, owner_field='user')

    ct = request.content_type or ''
    if ct.startswith('multipart/'):
        user_text = request.POST.get('message', '').strip()
        attachment = request.FILES.get('attachment')
        if attachment:
            raw = base64.b64encode(attachment.read()).decode()
            msg_content = json.dumps({
                'text': user_text,
                'attachments': [{'type': 'image', 'media_type': attachment.content_type, 'data': raw}],
            })
        else:
            msg_content = user_text
    else:
        data = json.loads(request.body)
        user_text = data.get('message', '').strip()
        msg_content = user_text

    if not user_text and not (ct.startswith('multipart/') and request.FILES.get('attachment')):
        return JsonResponse({'error': 'empty'}, status=400)

    Message.objects.create(conversation=conv, role='user', content=msg_content)
    if not conv.title:
        conv.auto_title()

    return JsonResponse({'ok': True, 'conv_id': conv.pk})


@login_required
def chat_stream(request, pk):
    conv = su_get(Conversation, pk, request.user, owner_field='user')
    history = [
        {'role': m['role'], 'content': _decode_content(m['content'])}
        for m in conv.messages.values('role', 'content')
    ]
    user = request.user

    system = _build_system(user)

    def _stream():
        client = _claude_client()
        msgs = list(history)
        full_text = ''

        for _ in range(10):  # max tool-use rounds
            with client.messages.stream(
                model=settings.CLAUDE_CHAT_MODEL,
                max_tokens=4096,
                system=system,
                tools=tools.DEFINITIONS,
                messages=msgs,
            ) as stream:
                for text in stream.text_stream:
                    full_text += text
                    yield f'data: {json.dumps({"t": text})}\n\n'
                msg = stream.get_final_message()

            if msg.stop_reason != 'tool_use':
                break

            # Build assistant content for history
            assistant_content = []
            for block in msg.content:
                if block.type == 'text':
                    assistant_content.append({'type': 'text', 'text': block.text})
                elif block.type == 'tool_use':
                    assistant_content.append({
                        'type': 'tool_use',
                        'id': block.id,
                        'name': block.name,
                        'input': block.input,
                    })
            msgs.append({'role': 'assistant', 'content': assistant_content})

            # Execute tools
            tool_results = []
            for block in msg.content:
                if block.type != 'tool_use':
                    continue
                preview = tools.args_preview(block.name, block.input)
                yield f'data: {json.dumps({"tool_call": block.name, "args_preview": preview})}\n\n'
                result = tools.execute(user, block.name, block.input)
                res_preview = tools.result_preview(block.name, result)
                yield f'data: {json.dumps({"tool_done": block.name, "result_preview": res_preview})}\n\n'
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': block.id,
                    'content': json.dumps(result),
                })

            msgs.append({'role': 'user', 'content': tool_results})

        if full_text:
            Message.objects.create(conversation=conv, role='assistant', content=full_text)
            conv.save(update_fields=['updated_at'])

        yield 'data: [DONE]\n\n'

    return StreamingHttpResponse(_stream(), content_type='text/event-stream')


@login_required
@require_POST
def chat_delete(request, pk):
    conv = su_get(Conversation, pk, request.user, owner_field='user')
    conv.delete()
    return JsonResponse({'ok': True})


# ── Document Templates ────────────────────────────────────────────────────────

@login_required
def templates_index(request):
    categories = TemplateCategory.objects.filter(active=True).prefetch_related('templates')
    return render(request, 'claude_ai/templates_index.html', {'categories': categories})


@login_required
def template_run(request, pk):
    tmpl = get_object_or_404(PromptTemplate, pk=pk, active=True)
    if request.method == 'POST':
        inputs = {v['name']: request.POST.get(v['name'], '') for v in tmpl.variables}
        prompt = tmpl.prompt_template
        for key, val in inputs.items():
            prompt = prompt.replace(f'{{{{{key}}}}}', val)

        return render(request, 'claude_ai/template_run.html', {
            'tmpl': tmpl,
            'inputs': inputs,
            'prompt': prompt,
            'streaming': True,
        })
    return render(request, 'claude_ai/template_run.html', {'tmpl': tmpl})


@login_required
def template_stream(request, pk):
    tmpl = get_object_or_404(PromptTemplate, pk=pk, active=True)
    prompt = request.GET.get('prompt', '')
    if not prompt:
        return JsonResponse({'error': 'no prompt'}, status=400)

    model = settings.CLAUDE_SMART_MODEL if tmpl.use_smart_model else settings.CLAUDE_CHAT_MODEL
    system = tmpl.system_prompt or _SYSTEM_DEFAULT

    def _stream():
        client = _claude_client()
        full = ''
        with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{'role': 'user', 'content': prompt}],
        ) as stream:
            for text in stream.text_stream:
                full += text
                yield f'data: {json.dumps({"t": text})}\n\n'

        GeneratedDocument.objects.create(
            user=request.user,
            template=tmpl,
            title=f'{tmpl.name} — {prompt[:60]}',
            content=full,
        )
        yield 'data: [DONE]\n\n'

    return StreamingHttpResponse(_stream(), content_type='text/event-stream')


@login_required
def documents_index(request):
    docs = su_qs(request.user, GeneratedDocument.objects, owner_field='user')
    return render(request, 'claude_ai/documents_index.html', {'docs': docs})


@login_required
def document_detail(request, pk):
    doc = su_get(GeneratedDocument, pk, request.user, owner_field='user')
    return render(request, 'claude_ai/document_detail.html', {'doc': doc})


@login_required
@require_POST
def document_delete(request, pk):
    doc = su_get(GeneratedDocument, pk, request.user, owner_field='user')
    doc.delete()
    return JsonResponse({'ok': True})


# ── Voice Notes ───────────────────────────────────────────────────────────────

@login_required
def voice_index(request):
    notes = su_qs(request.user, VoiceNote.objects, owner_field='user')
    return render(request, 'claude_ai/voice_index.html', {'notes': notes})


@login_required
@require_POST
def voice_transcribe(request):
    if not settings.OPENAI_API_KEY:
        return JsonResponse({'error': 'Transcription not configured'}, status=503)

    audio = request.FILES.get('audio')
    if not audio:
        return JsonResponse({'error': 'No audio'}, status=400)

    import openai
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
        for chunk in audio.chunks():
            f.write(chunk)
        tmp_path = f.name

    try:
        with open(tmp_path, 'rb') as f:
            result = client.audio.transcriptions.create(
                model=settings.WHISPER_MODEL,
                file=f,
                response_format='text',
            )
        transcript = result.strip()
    finally:
        os.unlink(tmp_path)

    note = VoiceNote.objects.create(
        user=request.user,
        transcript=transcript,
        linked_to=request.POST.get('linked_to', ''),
    )
    return JsonResponse({'ok': True, 'transcript': transcript, 'note_id': note.pk})


@login_required
@require_POST
def voice_delete(request, pk):
    note = su_get(VoiceNote, pk, request.user, owner_field='user')
    note.delete()
    return JsonResponse({'ok': True})
