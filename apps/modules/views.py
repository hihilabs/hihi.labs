from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .registry import MODULES


@login_required
def index(request):
    type_filter = request.GET.get('type', '')
    modules = MODULES
    if type_filter:
        modules = [m for m in modules if m['type'] == type_filter]
    return render(request, 'modules/index.html', {
        'modules': modules,
        'type_filter': type_filter,
        'types': sorted({m['type'] for m in MODULES}),
    })
