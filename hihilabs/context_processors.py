from django.conf import settings


def site_globals(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_OWNER': settings.SITE_OWNER,
    }
