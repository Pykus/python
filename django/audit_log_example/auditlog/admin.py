from django.contrib import admin

from .models import AuditEntry


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "actor",
        "action",
        "target_type",
        "target_key",
        "request_id",
    )
    list_filter = ("action", "target_type")
    search_fields = ("actor", "target_key", "request_id")
    readonly_fields = (
        "created_at",
        "actor",
        "action",
        "target_type",
        "target_key",
        "request_id",
        "metadata",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
