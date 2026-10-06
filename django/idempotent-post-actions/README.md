# Django idempotent POST actions and database constraints

Administrative applications often expose actions such as **approve**, **close**, **assign**, or **retry**. A double click, browser retry, reverse-proxy retry, or impatient user can submit the same POST twice. If the operation creates rows or triggers side effects, a normal `if not exists: create()` check is not enough: two concurrent requests can both pass the check.

## When to use this pattern

Use idempotency for operations where repeating the same logical command must not create another result: accepting an import, issuing a job, registering a payment reference, or approving a school/admin request. Do not add an idempotency layer to ordinary read-only GET requests, and do not use it as a replacement for correct database constraints.

A practical design combines three protections: a client-generated idempotency key, a database UNIQUE constraint, and a transaction. The database remains the final authority.

## Model

```python
from django.conf import settings
from django.db import models

class ExportJob(models.Model):
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=64)
    report_name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, default="queued")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["requested_by", "idempotency_key"],
                name="uniq_export_job_request",
            )
        ]
```

Scoping the key to the user lets two users safely use the same UUID. For a globally unique external request ID, constrain only that field.

## Transactional service

```python
from django.db import IntegrityError, transaction

@transaction.atomic
def request_export(*, user, key: str, report_name: str):
    try:
        job, created = ExportJob.objects.get_or_create(
            requested_by=user,
            idempotency_key=key,
            defaults={"report_name": report_name},
        )
    except IntegrityError:
        # A concurrent transaction may have won the race.
        job = ExportJob.objects.get(
            requested_by=user,
            idempotency_key=key,
        )
        created = False

    if not created and job.report_name != report_name:
        raise ValueError("Idempotency key was reused for different input")

    return job, created
```

The input comparison matters. Silently accepting the same key for a different payload can return a successful response for the wrong operation.

## HTTP view

```python
import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@require_POST
def create_export(request):
    key = request.headers.get("Idempotency-Key", "")
    try:
        uuid.UUID(key)
    except ValueError:
        return JsonResponse({"error": "invalid Idempotency-Key"}, status=400)

    try:
        job, created = request_export(
            user=request.user,
            key=key,
            report_name=request.POST["report_name"],
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=409)

    return JsonResponse(
        {"id": job.pk, "status": job.status},
        status=201 if created else 200,
    )
```

## Tests

```python
from django.test import TestCase

class ExportIdempotencyTests(TestCase):
    def test_repeated_key_returns_same_job(self):
        first, first_created = request_export(
            user=self.user, key=self.key, report_name="devices"
        )
        second, second_created = request_export(
            user=self.user, key=self.key, report_name="devices"
        )
        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ExportJob.objects.count(), 1)
```

Also test malformed keys, reuse with a different payload, two different keys, and concurrency with `TransactionTestCase` against the same database engine used in production.

## Common mistakes

Do not rely only on an in-memory cache: multiple application workers do not share process memory, and cache eviction can re-enable duplicates. Do not perform irreversible external work inside a transaction before the database state is durable. A safer design commits the job first and lets a worker process it; for stronger delivery guarantees, combine this with an outbox pattern.

SQLite can hide concurrency behavior that appears under PostgreSQL. Integration-test the critical race on the production database family.

## Verification checklist

1. Apply the migration and inspect the UNIQUE constraint in the database.
2. Submit one request and record the returned object ID.
3. Repeat it with the same key and payload; the ID must be identical.
4. Repeat the key with changed input; expect HTTP 409.
5. Fire concurrent requests with one key; exactly one database row must remain.
6. Confirm that retries do not duplicate background jobs or external side effects.

The important principle is that idempotency is a **data-integrity property**, not merely a UI convenience. The client key identifies the logical command, while the database constraint makes the guarantee survive concurrency and multiple Django workers.
