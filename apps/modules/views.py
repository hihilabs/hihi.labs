import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .registry import MODULES


@login_required
def index(request):
    type_filter = request.GET.get("type", "")
    modules = MODULES
    if type_filter:
        modules = [m for m in modules if m["type"] == type_filter]

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
    visible = [m for m in MODULES if m.get("description")]

    type_counts = {}
    for m in visible:
        t = m["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    type_filter = request.GET.get("type", "")
    displayed = [m for m in visible if not type_filter or m["type"] == type_filter]

    return render(request, "modules/works.html", {
        "modules":     displayed,
        "all_modules": visible,
        "type_filter": type_filter,
        "type_counts": type_counts,
        "total":       len(visible),
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
