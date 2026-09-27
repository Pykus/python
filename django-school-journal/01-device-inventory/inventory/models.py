from django.db import models

class Device(models.Model):
    hostname = models.CharField(max_length=63, unique=True)
    room = models.CharField(max_length=32, blank=True)
    online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["hostname"]

    def __str__(self) -> str:
        return self.hostname
