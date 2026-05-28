def footers(request):
    """Inject portal and public footer configs into every template context."""
    try:
        from .models import SiteFooter
        portal_footer = SiteFooter.get('portal')
        public_footer = SiteFooter.get('public')
    except Exception:
        portal_footer = None
        public_footer = None
    return {
        'portal_footer': portal_footer,
        'public_footer': public_footer,
    }
