from django.db import models


class GameServer(models.Model):
    name = models.CharField(max_length=100, default='Family Server')
    ip = models.CharField(max_length=45)
    port = models.PositiveIntegerField(default=22023)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.name} ({self.ip}:{self.port})'
