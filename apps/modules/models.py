from django.db import models


class HihiModule(models.Model):
    TYPE_CHOICES = [
        ('ai',      'AI / ML'),
        ('web',     'Web App'),
        ('cp',      'Community Playlist'),
        ('infra',   'Infrastructure'),
        ('utility', 'Utility'),
        ('tool',    'Tool / CLI'),
    ]
    STATUS_CHOICES = [
        ('live',     'Live'),
        ('beta',     'Beta'),
        ('wip',      'WIP'),
        ('archived', 'Archived'),
    ]

    # ── Identity ──────────────────────────────────────────────────────────────
    slug       = models.SlugField(max_length=120, unique=True)
    github_id  = models.IntegerField(unique=True, null=True, blank=True)

    # ── GitHub-synced (auto-updated on sync) ──────────────────────────────────
    github_name    = models.CharField(max_length=200, blank=True)
    github_url     = models.URLField(blank=True)
    github_desc    = models.TextField(blank=True)
    default_branch = models.CharField(max_length=100, default='main')
    language       = models.CharField(max_length=50, blank=True)
    topics         = models.JSONField(default=list)
    stars          = models.IntegerField(default=0)
    is_private     = models.BooleanField(default=False)
    last_pushed_at = models.DateTimeField(null=True, blank=True)
    synced_at      = models.DateTimeField(null=True, blank=True)

    # ── Curated metadata (manual / registry-seeded) ───────────────────────────
    name          = models.CharField(max_length=200)
    description   = models.TextField(blank=True)
    module_type   = models.CharField(max_length=20, choices=TYPE_CHOICES, default='web')
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='wip')
    platform      = models.CharField(max_length=100, blank=True)
    icon          = models.CharField(max_length=60, default='fa-code')
    icon_class    = models.CharField(max_length=20, default='fa-solid')
    color         = models.CharField(max_length=7, default='#7c6af7')
    live_url      = models.URLField(blank=True)
    source_url    = models.URLField(blank=True)
    tags          = models.JSONField(default=list)
    fleet_service = models.CharField(max_length=100, blank=True)
    notes         = models.TextField(blank=True)

    # ── Visibility ────────────────────────────────────────────────────────────
    is_public = models.BooleanField(default=False, db_index=True,
                                    help_text='Show on public Works page')
    is_active = models.BooleanField(default=True,  db_index=True)
    featured  = models.BooleanField(default=False)

    # ── Links to other apps ───────────────────────────────────────────────────
    managed_repo = models.OneToOneField(
        'gitnode.ManagedRepo', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='module',
        help_text='Linked deploy repo — enables git status / scoop / deploy',
    )
    project = models.ForeignKey(
        'projects.Project', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='modules',
        help_text='Linked project — wiki, time log, tasks, history',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module_type', 'name']

    def __str__(self):
        return self.name

    @property
    def effective_description(self):
        return self.description or self.github_desc

    @property
    def display_source_url(self):
        return self.source_url or self.github_url
