import json
import logging
from typing import Iterable

from django.conf import settings

logger = logging.getLogger(__name__)


def _claims():
    return {"sub": f"mailto:{settings.VAPID_CLAIM_EMAIL}"}


def send_push(subscription, payload: dict) -> bool:
    from pywebpush import webpush, WebPushException
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY_B64,
            vapid_claims=_claims(),
        )
        return True
    except WebPushException as exc:
        if getattr(exc.response, "status_code", None) in (404, 410):
            subscription.delete()
        else:
            logger.warning("Push failed: %s", exc)
        return False
    except Exception as exc:
        logger.warning("Push error: %s", exc)
        return False


def notify_user(user, payload: dict) -> int:
    from core.models import PushSubscription
    return sum(1 for s in PushSubscription.objects.filter(user=user) if send_push(s, payload))


def notify_all(payload: dict) -> int:
    from core.models import PushSubscription
    return sum(1 for s in PushSubscription.objects.all() if send_push(s, payload))
