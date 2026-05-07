import json
import os
import tempfile

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.projects.models import Project
from .models import Track, TrackComment


def _extract_duration(path):
    """Return duration in seconds. Falls back to 0 on any error."""
    try:
        import mutagen
        f = mutagen.File(path)
        if f is not None and hasattr(f, 'info'):
            return float(f.info.length)
    except Exception:
        pass
    try:
        import wave
        with wave.open(path, 'rb') as w:
            return w.getnframes() / w.getframerate()
    except Exception:
        pass
    return 0.0


@login_required
def index(request):
    tracks = Track.objects.filter(owner=request.user).select_related('project')
    projects = Project.objects.filter(owner=request.user, status='active')
    return render(request, 'sound/index.html', {
        'tracks': tracks,
        'projects': projects,
        'track_keys': Track.KEYS,
    })


@login_required
@require_POST
def track_upload(request):
    audio = request.FILES.get('audio')
    if not audio:
        return JsonResponse({'error': 'No file provided'}, status=400)

    title = request.POST.get('title', '').strip() or os.path.splitext(audio.name)[0]
    bpm_raw = request.POST.get('bpm', '').strip()
    bpm = int(bpm_raw) if bpm_raw.isdigit() else None
    project_id = request.POST.get('project_id') or None

    track = Track(
        owner=request.user,
        title=title,
        bpm=bpm,
        key=request.POST.get('key', ''),
        tags=request.POST.get('tags', ''),
        notes=request.POST.get('notes', ''),
    )
    if project_id:
        try:
            track.project = Project.objects.get(pk=project_id, owner=request.user)
        except Project.DoesNotExist:
            pass

    # Save file first so we have a path for duration extraction
    track.audio_file = audio
    track.save()

    duration = _extract_duration(track.audio_file.path)
    if duration:
        track.duration_s = duration
        track.save(update_fields=['duration_s'])

    return JsonResponse({'id': track.pk, 'title': track.title, 'duration': track.duration_display()})


@login_required
def track_detail(request, pk):
    import json as _json
    track = get_object_or_404(Track, pk=pk, owner=request.user)
    comments = list(track.comments.all())
    comments_json = _json.dumps([
        {'id': c.pk, 'ts': c.timestamp_s, 'display': c.timestamp_display(), 'body': c.body}
        for c in comments
    ])
    return render(request, 'sound/player.html', {
        'track': track,
        'comments': comments,
        'comments_json': comments_json,
    })


@login_required
@require_POST
def track_update(request, pk):
    """PATCH-style: update duration_s from client after WaveSurfer loads."""
    track = get_object_or_404(Track, pk=pk, owner=request.user)
    data = json.loads(request.body)
    if 'duration_s' in data and track.duration_s == 0:
        track.duration_s = float(data['duration_s'])
        track.save(update_fields=['duration_s'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def track_delete(request, pk):
    track = get_object_or_404(Track, pk=pk, owner=request.user)
    if track.audio_file:
        try:
            os.remove(track.audio_file.path)
        except OSError:
            pass
    track.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def comment_add(request, pk):
    track = get_object_or_404(Track, pk=pk, owner=request.user)
    data = json.loads(request.body)
    body = data.get('body', '').strip()
    timestamp_s = float(data.get('timestamp_s', 0))
    if not body:
        return JsonResponse({'error': 'Body required'}, status=400)
    c = TrackComment.objects.create(track=track, user=request.user, timestamp_s=timestamp_s, body=body)
    return JsonResponse({
        'id': c.pk,
        'timestamp_s': c.timestamp_s,
        'timestamp_display': c.timestamp_display(),
        'body': c.body,
        'user': request.user.get_short_name() or request.user.username,
    })


@login_required
@require_POST
def comment_delete(request, pk, comment_pk):
    track = get_object_or_404(Track, pk=pk, owner=request.user)
    TrackComment.objects.filter(pk=comment_pk, track=track).delete()
    return JsonResponse({'ok': True})
