"""Auto-maintained wiki documentation for modules.

Upserts a 'Modules (auto)' WikiSection with one child section per module —
refreshed on GitHub sync and on runner lifecycle changes, so the wiki
documents the module fleet without anyone touching it. Sections are
regenerated wholesale; don't hand-edit them (use the module's notes field
or a separate wiki section for curation).
"""
from django.utils import timezone

ROOT_SLUG = 'modules-auto'

_STATUS_ICON = {'live': '🟢', 'beta': '🟡', 'wip': '🟠', 'archived': '⚫'}
_RUN_ICON = {'running': '🟢', 'building': '🟡', 'cloning': '🟡',
             'error': '🔴', 'stopped': '⚫'}


def _root():
    from apps.wiki.models import WikiSection
    root, created = WikiSection.objects.get_or_create(
        slug=ROOT_SLUG,
        defaults={'title': 'Modules (auto)', 'order': 90},
    )
    if created or 'auto-generated' not in root.content_md:
        root.content_md = (
            '> **Auto-generated** — refreshed on every GitHub sync and every '
            'local run/stop. Hand edits here get overwritten; curate in each '
            "module's notes field instead.\n\n"
            f'_Last refresh: {timezone.now():%Y-%m-%d %H:%M}_'
        )
        root.save()
    return root


def _render(module):
    inst = getattr(module, 'instance', None)
    lines = [
        f'> auto-generated · {timezone.now():%Y-%m-%d %H:%M}',
        '',
        f'{_STATUS_ICON.get(module.status, "·")} **{module.name}** — '
        f'{module.get_module_type_display()} · {module.get_status_display()}'
        + (' · 🔒 private' if module.is_private else ''),
        '',
        module.effective_description or '_no description_',
        '',
    ]
    facts = []
    if module.github_url:
        facts.append(f'- Repo: [{module.github_name or module.slug}]({module.github_url})'
                     f' ({module.default_branch})')
    if module.language:
        facts.append(f'- Language: {module.language}')
    if module.live_url:
        facts.append(f'- Live: {module.live_url}')
    if module.last_pushed_at:
        facts.append(f'- Last push: {module.last_pushed_at:%Y-%m-%d}')
    if module.project_id:
        facts.append(f'- Project: {module.project.name} (`/projects/{module.project_id}/`)')
    if facts:
        lines += ['**Facts**', *facts, '']
    if inst:
        lines += [
            '**Local instance**',
            f'- Status: {_RUN_ICON.get(inst.status, "·")} {inst.status}',
        ]
        if inst.status == 'running':
            lines += [f'- URL: https://{inst.host}/ · direct :{inst.port}',
                      f'- Container: `{inst.container}`']
        lines.append(f'- Last change: {inst.updated_at:%Y-%m-%d %H:%M}')
        lines.append('')
    if module.notes:
        lines += ['**Notes (curated)**', module.notes, '']
    return '\n'.join(lines)


def update_module_page(module):
    """Idempotent upsert of the module's wiki section. Never raises."""
    try:
        from apps.wiki.models import WikiSection
        root = _root()
        sect, _ = WikiSection.objects.get_or_create(
            slug=f'module-{module.slug}'[:100],
            defaults={'title': module.name, 'parent': root},
        )
        sect.title = module.name
        sect.parent = root
        sect.content_md = _render(module)
        sect.save()
    except Exception:
        pass  # wiki doc is best-effort; never break sync/runner on it


def update_all():
    from .models import HihiModule
    for m in HihiModule.objects.filter(is_active=True).select_related('project'):
        update_module_page(m)
