from .models import Notification


def notify(user, type, title, body='', link=''):
    """Create an in-app notification. Call from anywhere in the codebase."""
    n = Notification.objects.create(user=user, type=type, title=title, body=body, link=link)

    # Also fire a push notification if the user has subscriptions
    try:
        from apps.core.models import PushSubscription
        from apps.core.push import send_push
        subs = PushSubscription.objects.filter(user=user)
        for sub in subs:
            send_push(sub, title, body, link)
    except Exception:
        pass

    return n
