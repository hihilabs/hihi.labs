import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.text import slugify
from .models import Service, ProjectService
from apps.core.superuser import su_qs, su_get


@login_required
def index(request):
    services = list(su_qs(request.user, Service.objects).prefetch_related('project_services__project'))
    try:
        from apps.projects.models import Project
        projects = list(su_qs(request.user, Project.objects).exclude(status='archived').order_by('name'))
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
    su_get(Service, pk, request.user).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def toggle(request, service_pk, project_pk):
    service = su_get(Service, service_pk, request.user)
    from apps.projects.models import Project
    project = su_get(Project, project_pk, request.user)
    ps, _ = ProjectService.objects.get_or_create(project=project, service=service)
    ps.enabled = not ps.enabled
    ps.save()
    return JsonResponse({'ok': True, 'enabled': ps.enabled})
