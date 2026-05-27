from django.conf import settings


def site_globals(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_OWNER': settings.SITE_OWNER,
    }


def css_version(request):
    from django.conf import settings
    return {'CSS_VER': getattr(settings, 'CSS_VER', '1')}
