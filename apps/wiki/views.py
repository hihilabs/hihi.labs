import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .models import WikiSection, WikiNote


def _build_tree(sections):
    """Return top-level sections with prefetched children (one level deep for now)."""
    by_id = {s.pk: s for s in sections}
    roots = []
    for s in sections:
        s.children_list = []
    for s in sections:
        if s.parent_id and s.parent_id in by_id:
            by_id[s.parent_id].children_list.append(s)
        elif not s.parent_id:
            roots.append(s)
    return roots


@login_required
def index(request):
    sections = list(
        WikiSection.objects.prefetch_related('notes').order_by('order', 'title')
    )
    roots = _build_tree(sections)
    return render(request, 'wiki/index.html', {'roots': roots, 'all_sections': sections})


@login_required
@require_POST
def section_create(request):
    data = json.loads(request.body)
    title = data.get('title', '').strip()
    parent_id = data.get('parent_id')
    if not title:
        return JsonResponse({'ok': False, 'error': 'title required'}, status=400)
    slug = slugify(title)
    base, n = slug, 1
    while WikiSection.objects.filter(slug=slug).exists():
        slug = f'{base}-{n}'; n += 1
    sec = WikiSection.objects.create(
        slug=slug, title=title,
        parent_id=parent_id or None,
        order=WikiSection.objects.count(),
        updated_by=request.user,
    )
    return JsonResponse({'ok': True, 'id': sec.pk, 'slug': sec.slug, 'title': sec.title,
                         'parent_id': sec.parent_id})


@login_required
@require_POST
def section_update(request, pk):
    sec = get_object_or_404(WikiSection, pk=pk)
    data = json.loads(request.body)
    for f in ['title', 'content_md', 'diagram_mermaid', 'order', 'collapsed']:
        if f in data:
            setattr(sec, f, data[f])
    sec.updated_by = request.user
    sec.save()
    return JsonResponse({'ok': True, 'updated_at': sec.updated_at.strftime('%b %-d, %-I:%M %p')})


@login_required
@require_POST
def section_delete(request, pk):
    sec = get_object_or_404(WikiSection, pk=pk)
    # Promote children to top-level before deleting
    WikiSection.objects.filter(parent=sec).update(parent=None)
    sec.delete()
    return JsonResponse({'ok': True})


# ── Notes ────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def note_create(request, section_pk):
    sec = get_object_or_404(WikiSection, pk=section_pk)
    data = json.loads(request.body)
    body = data.get('body', '').strip()
    if not body:
        return JsonResponse({'ok': False, 'error': 'body required'}, status=400)
    note = WikiNote.objects.create(
        section=sec, body=body,
        pinned=data.get('pinned', False),
        created_by=request.user,
    )
    return JsonResponse({
        'ok': True, 'id': note.pk, 'body': note.body,
        'pinned': note.pinned,
        'created_at': note.created_at.strftime('%b %-d'),
        'author': request.user.get_short_name() or request.user.username,
    })


@login_required
@require_POST
def note_update(request, pk):
    note = get_object_or_404(WikiNote, pk=pk)
    data = json.loads(request.body)
    if 'body' in data:
        note.body = data['body'].strip()
    if 'pinned' in data:
        note.pinned = data['pinned']
    note.save()
    return JsonResponse({'ok': True, 'body': note.body, 'pinned': note.pinned})


@login_required
@require_POST
def note_delete(request, pk):
    get_object_or_404(WikiNote, pk=pk).delete()
    return JsonResponse({'ok': True})
