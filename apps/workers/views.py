import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from .models import Client, WorkerNode, Job, JobType


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def index(request):
    workers  = WorkerNode.objects.all()
    clients  = Client.objects.filter(active=True)
    job_types= JobType.objects.all()
    recent   = Job.objects.select_related('client', 'job_type', 'worker').order_by('-created_at')[:100]

    queue_counts = {
        'queued':  Job.objects.filter(status='queued').count(),
        'running': Job.objects.filter(status__in=['claimed','running']).count(),
        'done':    Job.objects.filter(status='done').count(),
        'error':   Job.objects.filter(status='error').count(),
    }

    return render(request, 'workers/index.html', {
        'workers':      workers,
        'clients':      clients,
        'job_types':    job_types,
        'recent_jobs':  recent,
        'queue_counts': queue_counts,
    })


# ── Client management ─────────────────────────────────────────────────────────

@login_required
@require_POST
def client_add(request):
    data = json.loads(request.body)
    name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'name required'}, status=400)
    slug = name.lower().replace(' ', '_')
    c = Client.objects.create(
        name=name, slug=slug,
        color=data.get('color', '#7c6af7'),
        gpu_priority=int(data.get('gpu_priority', 50)),
        api_priority=int(data.get('api_priority', 50)),
        notes=data.get('notes', ''),
    )
    return JsonResponse({'id': c.pk, 'name': c.name, 'api_key': c.api_key})


@login_required
@require_POST
def client_update(request, pk):
    c    = get_object_or_404(Client, pk=pk)
    data = json.loads(request.body)
    for field in ('gpu_priority', 'api_priority', 'color', 'notes', 'active'):
        if field in data:
            setattr(c, field, data[field])
    c.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def client_delete(request, pk):
    get_object_or_404(Client, pk=pk).delete()
    return JsonResponse({'ok': True})


# ── Worker node management ────────────────────────────────────────────────────

@login_required
@require_POST
def worker_delete(request, pk):
    get_object_or_404(WorkerNode, pk=pk).delete()
    return JsonResponse({'ok': True})


# ── Job management ────────────────────────────────────────────────────────────

@login_required
@require_POST
def job_submit(request):
    data      = json.loads(request.body)
    client    = get_object_or_404(Client, slug=data.get('client', ''))
    job_type  = JobType.objects.filter(slug=data.get('job_type', '')).first()
    job = Job.objects.create(
        client=client,
        job_type=job_type,
        priority=int(data.get('priority', 5)),
        label=data.get('label', ''),
        payload=data.get('payload', {}),
    )
    return JsonResponse({'id': job.pk, 'status': job.status})


@login_required
@require_POST
def job_cancel(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if job.status in ('queued',):
        job.status = 'error'
        job.error  = 'Cancelled by user'
        job.save()
    return JsonResponse({'ok': True})


# ── Worker API (called by worker processes, auth via X-Worker-Key header) ─────

def _worker_auth(request):
    key  = request.headers.get('X-Worker-Key', '')
    node = WorkerNode.objects.filter(secret_key=key).first()
    return node


@csrf_exempt
def api_heartbeat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    body = json.loads(request.body)
    name = body.get('name', '')
    if not name:
        return JsonResponse({'error': 'name required'}, status=400)

    node, _ = WorkerNode.objects.get_or_create(name=name)
    node.last_seen   = timezone.now()
    node.worker_type = body.get('worker_type', node.worker_type or 'pull')
    node.ip          = request.META.get('REMOTE_ADDR')
    node.cpu_pct     = body.get('cpu_pct')
    node.mem_pct     = body.get('mem_pct')
    node.vram_used   = body.get('vram_used')
    node.vram_total  = body.get('vram_total')
    node.gpu         = body.get('gpu') or node.gpu
    node.active_jobs = body.get('active_jobs', 0)
    node.current_job = body.get('current_job')
    node.version     = body.get('version', node.version)
    if body.get('capabilities'):
        node.capabilities = body['capabilities']
    node.save()

    return JsonResponse({'ok': True, 'worker_id': node.pk})


@csrf_exempt
@require_GET
def api_jobs_pending(request):
    worker_name = request.GET.get('worker', '')
    job_type    = request.GET.get('type', '')

    qs = Job.objects.filter(status='queued').select_related('client', 'job_type')
    if job_type:
        qs = qs.filter(job_type__slug=job_type)

    # Order by client GPU priority × job priority
    jobs = sorted(qs[:50], key=lambda j: (
        -(j.client.gpu_priority * j.priority)
    ))[:10]

    return JsonResponse({'jobs': [
        {
            'id':       j.pk,
            'client':   j.client.slug,
            'type':     j.job_type.slug if j.job_type else None,
            'priority': j.priority,
            'label':    j.label,
            'payload':  j.payload,
        }
        for j in jobs
    ]})


@csrf_exempt
@require_POST
def api_job_claim(request, pk):
    body        = json.loads(request.body)
    worker_name = body.get('worker', '')
    job = get_object_or_404(Job, pk=pk)
    if job.status != 'queued':
        return JsonResponse({'error': 'already claimed'}, status=409)
    worker = WorkerNode.objects.filter(name=worker_name).first()
    job.status     = 'claimed'
    job.worker     = worker
    job.claimed_at = timezone.now()
    job.save()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def api_job_progress(request, pk):
    job  = get_object_or_404(Job, pk=pk)
    body = json.loads(request.body)
    job.status   = 'running'
    job.progress = body
    job.save(update_fields=['status', 'progress'])
    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def api_job_complete(request, pk):
    job  = get_object_or_404(Job, pk=pk)
    body = json.loads(request.body)
    job.status       = 'done'
    job.result       = body
    job.completed_at = timezone.now()
    job.save()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def api_job_error(request, pk):
    job  = get_object_or_404(Job, pk=pk)
    body = json.loads(request.body)
    job.status       = 'error'
    job.error        = body.get('error', '')[:2000]
    job.completed_at = timezone.now()
    job.save()
    return JsonResponse({'ok': True})


# ── Live data for dashboard polling ──────────────────────────────────────────

@login_required
def api_status(request):
    workers = []
    for w in WorkerNode.objects.all():
        workers.append({
            'id':          w.pk,
            'name':        w.name,
            'worker_type': w.worker_type,
            'online':      w.online,
            'ip':          w.ip,
            'gpu':         w.gpu,
            'cpu_pct':     w.cpu_pct,
            'mem_pct':     w.mem_pct,
            'vram_used':   w.vram_used,
            'vram_total':  w.vram_total,
            'active_jobs': w.active_jobs,
            'current_job': w.current_job,
            'age_s':       int((timezone.now() - w.last_seen).total_seconds()) if w.last_seen else None,
        })

    queue = []
    for j in Job.objects.filter(status__in=['queued','claimed','running']).select_related('client','job_type','worker').order_by('-priority','created_at')[:30]:
        queue.append({
            'id':       j.pk,
            'client':   j.client.name,
            'color':    j.client.color,
            'type':     j.job_type.slug if j.job_type else '—',
            'label':    j.label,
            'priority': j.priority,
            'status':   j.status,
            'worker':   j.worker.name if j.worker else None,
            'progress': j.progress,
            'age_s':    int((timezone.now() - j.created_at).total_seconds()),
        })

    return JsonResponse({'workers': workers, 'queue': queue})
