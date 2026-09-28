from django.db import models


class AuditEntry(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.CharField(max_length=254, db_index=True)
    action = models.CharField(max_length=120, db_index=True)
    target_type = models.CharField(max_length=80)
    target_key = models.CharField(max_length=200)
    request_id = models.CharField(max_length=100, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_type", "target_key"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.created_at:%Y-%m-%d %H:%M:%S} "
            f"{self.actor} {self.action} "
            f"{self.target_type}:{self.target_key}"
        )
