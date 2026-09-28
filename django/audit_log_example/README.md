# Django audit log application

This example is a small reusable Django application for recording administrative actions without mixing audit data into business models.

## What problem it solves

When an operator changes a device, account, configuration item, or another managed object, the application often needs a durable answer to four questions:

1. who performed the action;
2. what action was performed;
3. which object was affected;
4. when it happened and what non-sensitive context was attached.

The `auditlog` app below stores exactly that information and deliberately filters obvious secret-bearing metadata keys before writing JSON to the database.

## Files

- `auditlog/models.py` — indexed `AuditEntry` model;
- `auditlog/services.py` — single write API with metadata sanitization;
- `auditlog/admin.py` — read-oriented Django Admin view;
- `auditlog/tests.py` — tests for event creation and secret-key filtering.

## Integration

Copy the `auditlog` package into a Django project and add it to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "auditlog",
]
```

Then create the migration in the target project:

```bash
python manage.py makemigrations auditlog
python manage.py migrate
```

Record an event from a view or service:

```python
from auditlog.services import record_audit_event

record_audit_event(
    actor="operator@example.org",
    action="device.status.changed",
    target_type="device",
    target_key="host-a",
    request_id="req-example-001",
    metadata={"old_status": "offline", "new_status": "online"},
)
```

## Design notes

The audit log should contain enough context to explain an action, but it is not a dump of the request body. Passwords, tokens, cookies, authorization headers, and similar fields are filtered by the service. Applications with stricter requirements should use an explicit metadata allow-list.

The example uses synthetic identifiers only and has no dependency on a particular organization or infrastructure.
