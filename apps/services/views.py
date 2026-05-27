import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.text import slugify
from .models import Service, ProjectService


@login_required
def index(request):
    services = list(Service.objects.filter(owner=request.user).prefetch_related('project_services__project'))
    try:
        from apps.projects.models import Project
        projects = list(Project.objects.filter(owner=request.user).exclude(status='archived').order_by('name'))
    except Exception:
        projects = []
    return render(request, 'services/index.html', {'services': services, 'projects': projects})


@login_required
@require_POST
def create(request):
    data = json.loads(request.body)
    name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Name required'}, status=400)
    slug = slugify(name)
    if Service.objects.filter(slug=slug).exists():
        slug = f'{slug}-{Service.objects.count()}'
    s = Service.objects.create(
        owner=request.user, name=name, slug=slug,
        description=data.get('description', ''),
        icon=data.get('icon', 'fa-wrench'),
        color=data.get('color', '#7c6af7'),
        recurrence=data.get('recurrence', 'monthly'),
    )
    return JsonResponse({'ok': True, 'id': s.pk, 'name': s.name})


@login_required
@require_POST
def delete(request, pk):
    get_object_or_404(Service, pk=pk, owner=request.user).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def toggle(request, service_pk, project_pk):
    service = get_object_or_404(Service, pk=service_pk, owner=request.user)
    from apps.projects.models import Project
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    ps, _ = ProjectService.objects.get_or_create(project=project, service=service)
    ps.enabled = not ps.enabled
    ps.save()
    return JsonResponse({'ok': True, 'enabled': ps.enabled})
