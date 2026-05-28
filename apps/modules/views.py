import json
import os
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .registry import MODULES

_PUBLIC_PATH = os.path.join(os.path.dirname(__file__), 'public.json')


def _load_public():
    try:
        return json.load(open(_PUBLIC_PATH))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_public(flags):
    json.dump(flags, open(_PUBLIC_PATH, 'w'), indent=2, sort_keys=True)


@login_required
def index(request):
    type_filter = request.GET.get("type", "")
    flags = _load_public()

    modules = MODULES
    if type_filter:
        modules = [m for m in modules if m["type"] == type_filter]

    modules = [{**m, 'public': flags.get(m['slug'], False)} for m in modules]

    type_counts = {}
    for m in MODULES:
        t = m["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    return render(request, "modules/index.html", {
        "modules":     modules,
        "type_filter": type_filter,
        "types":       sorted(type_counts.keys()),
        "type_counts": type_counts,
        "total":       len(MODULES),
    })


def works_public(request):
    flags = _load_public()
    visible = [m for m in MODULES if flags.get(m['slug'], False)]

    type_counts = {}
    for m in visible:
        t = m["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    return render(request, "modules/works.html", {
        "modules":     visible,
        "type_counts": type_counts,
        "total":       len(visible),
    })


@login_required
@require_POST
def toggle_public(request):
    try:
        data = json.loads(request.body)
        slug = data['slug']
        value = bool(data['public'])
    except (KeyError, json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "invalid"}, status=400)

    # Validate slug exists in registry
    if not any(m['slug'] == slug for m in MODULES):
        return JsonResponse({"error": "unknown slug"}, status=404)

    flags = _load_public()
    flags[slug] = value
    _save_public(flags)
    return JsonResponse({"ok": True, "slug": slug, "public": value})


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
