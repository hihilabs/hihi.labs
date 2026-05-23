from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .registry import MODULES

# Top-level platform entries that have sub-modules
_PLATFORMS = {m['slug'] for m in MODULES if not m.get('parent')}


@login_required
def index(request):
    type_filter   = request.GET.get('type', '')
    parent_filter = request.GET.get('parent', '')

    modules = MODULES
    if type_filter:
        modules = [m for m in modules if m['type'] == type_filter]
    if parent_filter:
        modules = [m for m in modules if m.get('parent') == parent_filter]

    # Counts for the filter bar (exclude sub-modules from top-level counts)
    type_counts = {}
    for m in MODULES:
        t = m['type']
        type_counts[t] = type_counts.get(t, 0) + 1

    return render(request, 'modules/index.html', {
        'modules':       modules,
        'type_filter':   type_filter,
        'parent_filter': parent_filter,
        'types':         sorted(type_counts.keys()),
        'type_counts':   type_counts,
    })
