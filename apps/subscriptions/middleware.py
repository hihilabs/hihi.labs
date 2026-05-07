class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.subscription = None
        request.enabled_features = set()
        if request.user.is_authenticated:
            try:
                sub = request.user.subscription
                request.subscription = sub
                request.enabled_features = sub.enabled_features()
            except Exception:
                pass
        return self.get_response(request)
