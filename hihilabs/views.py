import json
from django.http import JsonResponse, FileResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_control
from django.shortcuts import render
from django.conf import settings


@cache_control(max_age=0, no_cache=True, no_store=True)
def service_worker(request):
    import os
    path = os.path.join(settings.BASE_DIR, "static", "sw.js")
    resp = FileResponse(open(path, "rb"), content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    return resp


def offline(request):
    return render(request, "offline.html")


@login_required
def push_vapid_key(request):
    return JsonResponse({"key": settings.VAPID_PUBLIC_KEY_B64})


@login_required
@require_POST
def push_subscribe(request):
    from apps.core.models import PushSubscription
    try:
        data   = json.loads(request.body)
        keys   = data.get("keys", {})
        PushSubscription.objects.update_or_create(
            endpoint=data["endpoint"],
            defaults={
                "user":       request.user,
                "p256dh":     keys.get("p256dh", ""),
                "auth":       keys.get("auth", ""),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300],
            },
        )
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "invalid"}, status=400)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def push_unsubscribe(request):
    from apps.core.models import PushSubscription
    try:
        data = json.loads(request.body)
        PushSubscription.objects.filter(endpoint=data["endpoint"]).delete()
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "invalid"}, status=400)
    return JsonResponse({"ok": True})
