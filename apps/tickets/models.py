from django.db import models
from django.contrib.auth.models import User


class Ticket(models.Model):
    STATUS   = [('open','Open'),('in_progress','In Progress'),('resolved','Resolved'),('closed','Closed')]
    TYPE     = [('bug','Bug'),('feature','Feature'),('request','Request'),('question','Question')]
    PRIORITY = [('low','Low'),('normal','Normal'),('high','High'),('urgent','Urgent')]

    project  = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE, null=True, blank=True,
        related_name='tickets',
    )
    reporter         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_tickets')
    submitter_name   = models.CharField(max_length=200, blank=True)
    submitter_email  = models.EmailField(blank=True)
    title    = models.CharField(max_length=300)
    body     = models.TextField(blank=True)
    status   = models.CharField(max_length=20,  choices=STATUS,   default='open')
    type     = models.CharField(max_length=20,  choices=TYPE,     default='request')
    priority = models.CharField(max_length=10,  choices=PRIORITY, default='normal')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def status_color(self):
        return {'open':'var(--yellow)','in_progress':'var(--brand)','resolved':'var(--green)','closed':'var(--text-muted)'}.get(self.status,'var(--text-muted)')


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_comments')
    body   = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment on #{self.ticket.pk} by {self.author}'
