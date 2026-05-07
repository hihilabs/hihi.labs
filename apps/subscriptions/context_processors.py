def subscription_context(request):
    sub = getattr(request, 'subscription', None)
    features = getattr(request, 'enabled_features', set())
    return {
        'subscription': sub,
        'enabled_features': features,
    }
