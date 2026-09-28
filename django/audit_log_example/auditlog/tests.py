from django.test import TestCase

from .models import AuditEntry
from .services import record_audit_event, sanitize_metadata


class AuditLogTests(TestCase):
    def test_record_audit_event_creates_queryable_entry(self) -> None:
        entry = record_audit_event(
            actor="operator@example.org",
            action="device.status.changed",
            target_type="device",
            target_key="host-a",
            request_id="req-example-001",
            metadata={"old_status": "offline", "new_status": "online"},
        )

        stored = AuditEntry.objects.get(pk=entry.pk)
        self.assertEqual(stored.actor, "operator@example.org")
        self.assertEqual(stored.metadata["new_status"], "online")

    def test_sanitizer_removes_obvious_secret_fields_recursively(self) -> None:
        clean = sanitize_metadata(
            {
                "reason": "manual verification",
                "api_token": "do-not-store",
                "nested": {
                    "password": "do-not-store",
                    "result": "ok",
                },
            }
        )

        self.assertNotIn("api_token", clean)
        self.assertNotIn("password", clean["nested"])
        self.assertEqual(clean["nested"]["result"], "ok")

    def test_required_identity_fields_are_enforced(self) -> None:
        with self.assertRaises(ValueError):
            record_audit_event(
                actor="",
                action="device.updated",
                target_type="device",
                target_key="host-a",
            )
