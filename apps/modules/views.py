import json
import urllib.request

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from .models import HihiModule

GITHUB_ORG   = getattr(settings, 'GITHUB_ORG',   'hihilabs')
GITHUB_TOKEN = getattr(settings, 'GITHUB_TOKEN',  '')


# ── GitHub helpers ─────────────────────────────────────────────────────────────

def _github_get(url):
    req = urllib.request.Request(url)
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('User-Agent', 'hihilabs-modules/1.0')
    if GITHUB_TOKEN:
        req.add_header('Authorization', f'token {GITHUB_TOKEN}')
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _fetch_org_repos():
    repos, page = [], 1
    while True:
        batch = _github_get(
            f'https://api.github.com/orgs/{GITHUB_ORG}/repos'
            f'?per_page=100&page={page}&type=all'
        )
        if not batch:
            break
        repos.extend(batch)
        page += 1
        if len(batch) < 100:
            break
    return repos


# ── Staff views ───────────────────────────────────────────────────────────────

@staff_member_required
def index(request):
    qs = HihiModule.objects.filter(is_active=True).select_related('managed_repo__server')

    type_filter   = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    search        = request.GET.get('q', '').strip()

    if type_filter:   qs = qs.filter(module_type=type_filter)
    if status_filter: qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(name__icontains=search)

    all_active  = HihiModule.objects.filter(is_active=True)
    type_counts = {}
    for m in all_active:
        type_counts[m.module_type] = type_counts.get(m.module_type, 0) + 1

    last_sync = (HihiModule.objects
                 .filter(synced_at__isnull=False)
                 .order_by('-synced_at')
                 .values_list('synced_at', flat=True)
                 .first())

    return render(request, 'modules/index.html', {
        'modules':        qs.order_by('module_type', 'name'),
        'type_filter':    type_filter,
        'status_filter':  status_filter,
        'search':         search,
        'type_counts':    type_counts,
        'type_choices':   HihiModule.TYPE_CHOICES,
        'status_choices': HihiModule.STATUS_CHOICES,
        'total':          all_active.count(),
        'public_count':   HihiModule.objects.filter(is_public=True, is_active=True).count(),
        'last_sync':      last_sync,
    })


@staff_member_required
@require_POST
def sync_github(request):
    """Pull all repos from the hihilabs GitHub org and upsert HihiModule records."""
    try:
        repos = _fetch_org_repos()
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})

    now = timezone.now()
    created = updated = 0

    for repo in repos:
        slug = repo['name'].lower()
        pushed = None
        if repo.get('pushed_at'):
            try:
                pushed = parse_datetime(repo['pushed_at'])
            except Exception:
                pass

        obj, is_new = HihiModule.objects.get_or_create(
            github_id=repo['id'],
            defaults={'slug': slug, 'name': repo['name']},
        )

        # Always refresh GitHub-sourced fields
        obj.github_name    = repo['name']
        obj.github_url     = repo.get('html_url', '')
        obj.github_desc    = repo.get('description') or ''
        obj.default_branch = repo.get('default_branch', 'main')
        obj.language       = repo.get('language') or ''
        obj.topics         = repo.get('topics', [])
        obj.stars          = repo.get('stargazers_count', 0)
        obj.is_private     = repo.get('private', False)
        obj.last_pushed_at = pushed
        obj.synced_at      = now

        if is_new:
            obj.source_url = repo.get('html_url', '')

        obj.save()
        if is_new:
            created += 1
        else:
            updated += 1

    return JsonResponse({'ok': True, 'created': created, 'updated': updated, 'total': len(repos)})


@staff_member_required
@require_POST
def seed_registry(request):
    """One-time import of registry.py metadata into HihiModule records."""
    from .registry import MODULES
    created = updated = 0
    for m in MODULES:
        obj, is_new = HihiModule.objects.get_or_create(slug=m['slug'])
        obj.name          = m.get('name', m['slug'])
        obj.description   = m.get('description', '')
        obj.module_type   = m.get('type', 'web')
        obj.status        = m.get('status', 'wip')
        obj.platform      = m.get('platform', '')
        obj.icon          = m.get('icon', 'fa-code')
        obj.icon_class    = m.get('icon_class', 'fa-solid')
        obj.color         = m.get('color', '#7c6af7')
        obj.live_url      = m.get('live_url', '')
        obj.source_url    = m.get('source_url', '')
        obj.tags          = m.get('tags', [])
        obj.fleet_service = m.get('fleet_service', '')
        obj.is_active     = True
        obj.save()
        if is_new:
            created += 1
        else:
            updated += 1
    return JsonResponse({'ok': True, 'created': created, 'updated': updated, 'total': len(MODULES)})


@staff_member_required
@require_POST
def toggle_public(request, pk):
    m = get_object_or_404(HihiModule, pk=pk)
    m.is_public = not m.is_public
    m.save(update_fields=['is_public', 'updated_at'])
    return JsonResponse({'ok': True, 'is_public': m.is_public})


@staff_member_required
@require_POST
def update_field(request, pk):
    m = get_object_or_404(HihiModule, pk=pk)
    allowed = [
        'module_type', 'status', 'platform', 'color', 'icon', 'icon_class',
        'live_url', 'source_url', 'name', 'description', 'notes',
        'fleet_service', 'featured',
    ]
    changed = []
    for f in allowed:
        v = request.POST.get(f)
        if v is not None:
            setattr(m, f, v == '1' if f == 'featured' else v)
            changed.append(f)
    if changed:
        m.save(update_fields=changed + ['updated_at'])
    return JsonResponse({'ok': True, 'changed': changed})


# ── Public views ──────────────────────────────────────────────────────────────

def works_public(request):
    modules = (HihiModule.objects
               .filter(is_public=True, is_active=True)
               .order_by('module_type', 'name'))
    type_counts = {}
    for m in modules:
        type_counts[m.module_type] = type_counts.get(m.module_type, 0) + 1
    return render(request, 'modules/works.html', {
        'modules':     modules,
        'type_counts': type_counts,
        'total':       modules.count(),
    })


@require_POST
def contact(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "invalid"}, status=400)

    name     = data.get("name", "").strip()[:100]
    email    = data.get("email", "").strip()[:200]
    message  = data.get("message", "").strip()[:2000]
    interest = data.get("interest", "").strip()[:50]

    if not name or not email or not message:
        return JsonResponse({"error": "name, email, and message required"}, status=400)

    from django.contrib.auth.models import User
    from apps.messaging.models import Notification
    body_preview = "{} <{}> [{}]: {}".format(name, email, interest, message[:120])
    for admin in User.objects.filter(is_superuser=True):
        Notification.objects.create(
            user=admin, type="system",
            title="Works inquiry - {}".format(name),
            body=body_preview, link="/modules/",
        )
    return JsonResponse({"ok": True})
