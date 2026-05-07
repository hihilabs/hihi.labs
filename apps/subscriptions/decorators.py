from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def require_feature(feature):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if feature not in request.enabled_features:
                return redirect('subscriptions:upgrade')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
