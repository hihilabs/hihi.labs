import json
import os
import secrets
import tempfile
import time

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Whiteboard, RoomEvent, Sandbox
from . import sandbox as sandbox_engine
from apps.core.superuser import su_qs, su_get


@login_required
def index(request):
    boards = su_qs(request.user, Whiteboard.objects)
    from apps.projects.models import Project
    projects = su_qs(request.user, Project.objects).exclude(status='archived')
    return render(request, 'whiteboards/index.html', {'boards': boards, 'projects': projects})


def _room_board(pk, user):
    """Rooms are collaborative — any staff member may open/save any board."""
    if user.is_superuser or user.is_staff:
        return get_object_or_404(Whiteboard, pk=pk)
    return su_get(Whiteboard, pk, user)


@login_required
def detail(request, pk):
    board = _room_board(pk, request.user)
    events = board.events.select_related('user').order_by('created_at')[:200]
    return render(request, 'whiteboards/canvas.html', {'board': board, 'events': events})


@login_required
@require_POST
def create(request):
    data = json.loads(request.body)
    title = data.get('title', 'Untitled').strip() or 'Untitled'
    project_id = data.get('project_id') or None
    board = Whiteboard.objects.create(owner=request.user, title=title, project_id=project_id)
    return JsonResponse({'ok': True, 'id': board.pk})


@login_required
@require_POST
def save(request, pk):
    board = _room_board(pk, request.user)
    data = json.loads(request.body)
    board.data = json.dumps(data.get('canvas', {}))
    if 'title' in data:
        board.title = data['title'].strip() or board.title
    board.save(update_fields=['data', 'title', 'updated_at'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def delete(request, pk):
    su_get(Whiteboard, pk, request.user).delete()
    return JsonResponse({'ok': True})


@login_required
def rtc_token(request, pk):
    board = _room_board(pk, request.user)
    if not settings.LIVEKIT_API_SECRET:
        return JsonResponse({'error': 'LiveKit not configured'}, status=503)
    import jwt
    now = int(time.time())
    # Random suffix so the same user in two tabs doesn't kick themselves
    identity = f'{request.user.username}-{secrets.token_hex(3)}'
    token = jwt.encode({
        'iss': settings.LIVEKIT_API_KEY,
        'sub': identity,
        'name': request.user.get_short_name() or request.user.username,
        'nbf': now - 10,
        'exp': now + 6 * 3600,
        'video': {'room': f'wb-{board.pk}', 'roomJoin': True,
                  'canPublish': True, 'canSubscribe': True},
    }, settings.LIVEKIT_API_SECRET, algorithm='HS256')
    return JsonResponse({'token': token, 'url': settings.LIVEKIT_CLIENT_URL,
                         'identity': identity})


@login_required
@require_POST
def speech(request, pk):
    """Receive a short mic chunk, transcribe via Whisper, append to the
    room transcript and broadcast to everyone connected."""
    board = _room_board(pk, request.user)
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
                model=settings.WHISPER_MODEL, file=f, response_format='text')
        transcript = result.strip()
    finally:
        os.unlink(tmp_path)

    if len(transcript) < 2:
        return JsonResponse({'ok': True, 'skipped': True})

    ev = RoomEvent.objects.create(board=board, user=request.user,
                                  kind='speech', text=transcript)
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    async_to_sync(get_channel_layer().group_send)(f'room_{board.pk}', {
        'type': 'room.relay', 'src': None,
        'payload': {'t': 'event', 'event': {
            'id': ev.pk, 'kind': 'speech', 'text': transcript, 'meta': {},
            'user': request.user.get_short_name() or request.user.username,
            'ts': ev.created_at.strftime('%-I:%M %p'),
        }},
    })
    return JsonResponse({'ok': True, 'text': transcript})


def _room_broadcast(board_pk, kind, text, user=None, meta=None):
    """Persist a RoomEvent and push it to everyone in the room."""
    ev = RoomEvent.objects.create(board_id=board_pk, user=user, kind=kind,
                                  text=text, meta=meta or {})
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    async_to_sync(get_channel_layer().group_send)(f'room_{board_pk}', {
        'type': 'room.relay', 'src': None,
        'payload': {'t': 'event', 'event': {
            'id': ev.pk, 'kind': kind, 'text': text, 'meta': ev.meta,
            'user': (user.get_short_name() or user.username) if user else '',
            'ts': ev.created_at.strftime('%-I:%M %p'),
        }},
    })


def _sandbox_payload(sb):
    return {'id': sb.pk, 'template': sb.template, 'status': sb.status,
            'url': sandbox_engine.url_for(sb) if sb.status == 'running' else ''}


def _module_payload(m):
    from apps.modules import runner as module_runner
    inst = getattr(m, 'instance', None)
    return {
        'pk': m.pk, 'slug': m.slug, 'name': m.name,
        'desc': (m.effective_description or '')[:80],
        'status': inst.status if inst else 'none',
        'url': f'https://{inst.host}/' if inst and inst.status == 'running' else '',
        'direct': f'http://{module_runner.BIND_IP}:{inst.port}/'
                  if inst and inst.status == 'running' and inst.port else '',
    }


@login_required
def sandbox_state(request, pk):
    board = _room_board(pk, request.user)
    from apps.modules.models import HihiModule
    modules = [_module_payload(m) for m in
               HihiModule.objects.filter(is_active=True).exclude(github_url='')
               .order_by('slug')]
    return JsonResponse({
        'templates': [{'key': k, 'label': t['label'], 'desc': t['desc']}
                      for k, t in sandbox_engine.TEMPLATES.items()],
        'sandboxes': [_sandbox_payload(s) for s in
                      board.sandboxes.filter(status='running')],
        'modules': modules,
    })


@login_required
@require_POST
def room_module_run(request, pk, module_pk):
    """Spin a real module from inside a room and announce it in the transcript."""
    board = _room_board(pk, request.user)
    from apps.modules.models import HihiModule
    from apps.modules import runner as module_runner
    module = get_object_or_404(HihiModule, pk=module_pk)
    module_runner.start(module, request.user)
    who = request.user.get_short_name() or request.user.username
    _room_broadcast(board.pk, 'sandbox',
                    f'{who} is spinning up module "{module.slug}" — cloning/building, '
                    f'watch /modules/ or ask again in a minute',
                    user=request.user, meta={'module_pk': module.pk, 'slug': module.slug})
    return JsonResponse({'ok': True, 'module_pk': module.pk})


@login_required
@require_POST
def sandbox_new(request, pk):
    board = _room_board(pk, request.user)
    data = json.loads(request.body)
    try:
        sb = sandbox_engine.spin(board, data.get('template', ''), request.user)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    _room_broadcast(board.pk, 'sandbox',
                    f'{request.user.get_short_name() or request.user.username} '
                    f'spun up a {sb.template} sandbox → {sandbox_engine.url_for(sb)}',
                    user=request.user, meta=_sandbox_payload(sb))
    return JsonResponse(_sandbox_payload(sb))


@login_required
@require_POST
def sandbox_stop(request, pk, sb_pk):
    board = _room_board(pk, request.user)
    sb = get_object_or_404(Sandbox, pk=sb_pk, board=board)
    sandbox_engine.stop(sb)
    _room_broadcast(board.pk, 'sandbox', f'sandbox {sb.pk} ({sb.template}) stopped',
                    user=request.user, meta=_sandbox_payload(sb))
    return JsonResponse({'ok': True})


@login_required
def sandbox_files(request, pk, sb_pk):
    board = _room_board(pk, request.user)
    sb = get_object_or_404(Sandbox, pk=sb_pk, board=board)
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            target = sandbox_engine.safe_path(sb, data['path'])
        except ValueError:
            return JsonResponse({'error': 'Bad path'}, status=400)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data.get('content', ''))
        _room_broadcast(board.pk, 'sandbox',
                        f'{request.user.get_short_name() or request.user.username} '
                        f'edited {data["path"]} in sandbox {sb.pk}', user=request.user)
        return JsonResponse({'ok': True})
    rel = request.GET.get('path', '')
    if rel:
        try:
            target = sandbox_engine.safe_path(sb, rel)
        except ValueError:
            return JsonResponse({'error': 'Bad path'}, status=400)
        if not target.is_file():
            return JsonResponse({'error': 'Not found'}, status=404)
        return JsonResponse({'path': rel, 'content': target.read_text(errors='replace')})
    return JsonResponse({'files': sandbox_engine.list_files(sb)})
