from django.db import models
from django.contrib.auth.models import User


class Track(models.Model):
    KEYS = [
        ('', '—'), ('C', 'C'), ('Cm', 'Cm'), ('C#', 'C#'), ('C#m', 'C#m'),
        ('D', 'D'), ('Dm', 'Dm'), ('Eb', 'Eb'), ('Ebm', 'Ebm'),
        ('E', 'E'), ('Em', 'Em'), ('F', 'F'), ('Fm', 'Fm'),
        ('F#', 'F#'), ('F#m', 'F#m'), ('G', 'G'), ('Gm', 'Gm'),
        ('Ab', 'Ab'), ('Abm', 'Abm'), ('A', 'A'), ('Am', 'Am'),
        ('Bb', 'Bb'), ('Bbm', 'Bbm'), ('B', 'B'), ('Bm', 'Bm'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tracks')
    title = models.CharField(max_length=200)
    audio_file = models.FileField(upload_to='tracks/')
    duration_s = models.FloatField(default=0)
    bpm = models.IntegerField(null=True, blank=True)
    key = models.CharField(max_length=4, choices=KEYS, blank=True)
    tags = models.CharField(max_length=300, blank=True, help_text='Comma-separated')
    notes = models.TextField(blank=True)
    project = models.ForeignKey(
        'projects.Project', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='tracks',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def duration_display(self):
        s = int(self.duration_s)
        m, sec = divmod(s, 60)
        return f'{m}:{sec:02d}'

    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]


class TrackComment(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='track_comments')
    timestamp_s = models.FloatField()
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp_s']

    def __str__(self):
        return f'{self.track.title} @ {self.timestamp_s:.1f}s'

    def timestamp_display(self):
        s = int(self.timestamp_s)
        m, sec = divmod(s, 60)
        return f'{m}:{sec:02d}'
