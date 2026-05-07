import json
import os
import tempfile

import anthropic
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from . import tools
from .models import Conversation, Message, PromptTemplate, TemplateCategory, GeneratedDocument, VoiceNote


_SYSTEM_DEFAULT = (
    "You are HiHi — a sharp, concise AI assistant embedded in Andrew's personal business OS at hihilabs.xyz. "
    "Andrew is a solo full-stack developer/architect running FCKRY LLC dba CommunityPlaylist. "
    "He works on Django, Python, PHP, audio tools, hosting, and creative client work. "
    "Be direct, practical, no filler. Markdown is fine.\n\n"
    "You have tools to manage Andrew's business and codebase:\n"
    "— Data: list/create/update projects, tasks, time entries, servers\n"
    "— Files: read_file, write_file, list_dir on the hihilabs source at /workspace/\n"
    "— Django: run_manage for migrate, makemigrations, etc.\n"
    "— Rebuild: docker_rebuild restarts the container (60-90s)\n\n"
    "Hot-reload rules — gunicorn --reload is active, so:\n"
    "  • Python files (.py) and templates (.html) → live immediately after write_file, NO rebuild needed\n"
    "  • Static files (CSS/JS in static/) → call docker_rebuild after writing\n"
    "  • requirements.txt changes → call docker_rebuild after writing\n"
    "Use tools proactively — when the request involves real data or a code change, do it. "
    "For file edits: read first, then write the complete updated file content."
)


def _claude_client():
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# ── Chat ─────────────────────────────────────────────────────────────────────

@login_required
def chat_index(request):
    conversations = Conversation.objects.filter(user=request.user)
    return render(request, 'claude_ai/chat_index.html', {'conversations': conversations})


@login_required
def chat_new(request):
    conv = Conversation.objects.create(user=request.user)
    return redirect('ai:chat', pk=conv.pk)


@login_required
def chat_detail(request, pk):
    conv = get_object_or_404(Conversation, pk=pk, user=request.user)
    messages = conv.messages.all()
    conversations = Conversation.objects.filter(user=request.user)
    return render(request, 'claude_ai/chat.html', {
        'conv': conv,
        'messages': messages,
        'conversations': conversations,
    })


@login_required
@require_POST
def chat_send(request, pk):
    conv = get_object_or_404(Conversation, pk=pk, user=request.user)
    data = json.loads(request.body)
    user_text = data.get('message', '').strip()
    if not user_text:
        return JsonResponse({'error': 'empty'}, status=400)

    Message.objects.create(conversation=conv, role='user', content=user_text)
    if not conv.title:
        conv.auto_title()

    return JsonResponse({'ok': True, 'conv_id': conv.pk})


@login_required
def chat_stream(request, pk):
    conv = get_object_or_404(Conversation, pk=pk, user=request.user)
    history = list(conv.messages.values('role', 'content'))
    user = request.user

    def _stream():
        client = _claude_client()
        msgs = list(history)
        full_text = ''

        for _ in range(10):  # max tool-use rounds
            with client.messages.stream(
                model=settings.CLAUDE_CHAT_MODEL,
                max_tokens=4096,
                system=_SYSTEM_DEFAULT,
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
                yield f'data: {json.dumps({"tool_call": block.name})}\n\n'
                result = tools.execute(user, block.name, block.input)
                yield f'data: {json.dumps({"tool_done": block.name})}\n\n'
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
    conv = get_object_or_404(Conversation, pk=pk, user=request.user)
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
    docs = GeneratedDocument.objects.filter(user=request.user)
    return render(request, 'claude_ai/documents_index.html', {'docs': docs})


@login_required
def document_detail(request, pk):
    doc = get_object_or_404(GeneratedDocument, pk=pk, user=request.user)
    return render(request, 'claude_ai/document_detail.html', {'doc': doc})


@login_required
@require_POST
def document_delete(request, pk):
    doc = get_object_or_404(GeneratedDocument, pk=pk, user=request.user)
    doc.delete()
    return JsonResponse({'ok': True})


# ── Voice Notes ───────────────────────────────────────────────────────────────

@login_required
def voice_index(request):
    notes = VoiceNote.objects.filter(user=request.user)
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
    note = get_object_or_404(VoiceNote, pk=pk, user=request.user)
    note.delete()
    return JsonResponse({'ok': True})
