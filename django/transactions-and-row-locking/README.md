# Django transactions and row locking

Database race conditions are easy to miss because the code often works perfectly during manual testing. Problems appear only when two requests modify the same data at nearly the same time.

This guide shows how to use Django transactions, `transaction.atomic()`, `select_for_update()`, constraints, and retry-aware patterns to protect operations that must remain consistent.

The examples use a small inventory/reservation domain, but the same techniques apply to:

- booking systems,
- stock counters,
- ticket allocation,
- payment state transitions,
- school resource reservations,
- workflow approvals,
- job queues,
- counters and quotas,
- any operation where two users may update the same row concurrently.

## 1. The race condition

Suppose a table stores available devices:

```python
from django.db import models


class DevicePool(models.Model):
    name = models.CharField(max_length=100)
    available = models.PositiveIntegerField(default=0)
```

A naive reservation function:

```python
def reserve_one(pool_id):
    pool = DevicePool.objects.get(pk=pool_id)

    if pool.available < 1:
        raise ValueError("No devices available")

    pool.available -= 1
    pool.save(update_fields=["available"])
```

This looks correct, but two requests can execute like this:

```text
Request A reads available = 1
Request B reads available = 1
Request A writes available = 0
Request B writes available = 0
```

Both requests think they succeeded, even though only one device existed.

This is a classic lost-update / race-condition problem.

## 2. transaction.atomic()

`transaction.atomic()` groups database operations into one transaction.

```python
from django.db import transaction


def create_order():
    with transaction.atomic():
        order = Order.objects.create(status="pending")
        OrderLine.objects.create(
            order=order,
            product_id=123,
            quantity=1,
        )

    return order
```

If creating the line fails, the order creation is rolled back too.

This protects multi-step consistency, but it does not automatically prevent two transactions from reading and modifying the same row at the same time.

For that, use row locking.

## 3. select_for_update()

`select_for_update()` asks the database to lock selected rows until the surrounding transaction ends.

```python
from django.db import transaction


def reserve_one(pool_id):
    with transaction.atomic():
        pool = (
            DevicePool.objects
            .select_for_update()
            .get(pk=pool_id)
        )

        if pool.available < 1:
            raise ValueError(
                "No devices available"
            )

        pool.available -= 1
        pool.save(
            update_fields=["available"]
        )
```

Now the second request waits until the first transaction finishes before reading the locked row.

The sequence becomes:

```text
Request A locks row
Request A reads available = 1
Request B waits
Request A writes available = 0
Request A commits
Request B acquires lock
Request B reads available = 0
Request B rejects reservation
```

That is the behavior we want.

## 4. select_for_update() requires a transaction

This is incorrect:

```python
pool = (
    DevicePool.objects
    .select_for_update()
    .get(pk=pool_id)
)
```

The lock is useful only inside an active transaction.

Use:

```python
with transaction.atomic():
    pool = (
        DevicePool.objects
        .select_for_update()
        .get(pk=pool_id)
    )
```

## 5. Lock only the rows you need

Do not lock an entire table if one row is enough.

Good:

```python
with transaction.atomic():
    pool = (
        DevicePool.objects
        .select_for_update()
        .get(pk=pool_id)
    )
```

Less desirable:

```python
with transaction.atomic():
    pools = list(
        DevicePool.objects
        .select_for_update()
        .all()
    )
```

Large lock scopes increase contention and can reduce throughput.

## 6. Example: booking a room

Models:

```python
from django.db import models


class Room(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )


class Booking(models.Model):
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
    )
```

A safe booking service:

```python
from django.db import transaction


def create_booking(
    *,
    room_id,
    starts_at,
    ends_at,
    user,
):
    if starts_at >= ends_at:
        raise ValueError(
            "starts_at must be before ends_at"
        )

    with transaction.atomic():
        room = (
            Room.objects
            .select_for_update()
            .get(pk=room_id)
        )

        overlap = Booking.objects.filter(
            room=room,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        ).exists()

        if overlap:
            raise ValueError(
                "Room is already booked"
            )

        return Booking.objects.create(
            room=room,
            starts_at=starts_at,
            ends_at=ends_at,
            created_by=user,
        )
```

Locking the room serializes booking attempts for the same room.

## 7. Put concurrency rules in a service layer

Avoid spreading transaction logic across views.

View:

```python
from django.http import JsonResponse


def reserve_device_view(request):
    reservation = reserve_device(
        pool_id=request.POST["pool_id"],
        user=request.user,
    )

    return JsonResponse(
        {
            "reservation_id":
                reservation.id,
        }
    )
```

Service:

```python
from django.db import transaction


def reserve_device(*, pool_id, user):
    with transaction.atomic():
        pool = (
            DevicePool.objects
            .select_for_update()
            .get(pk=pool_id)
        )

        if pool.available <= 0:
            raise NoAvailability()

        pool.available -= 1
        pool.save(
            update_fields=["available"]
        )

        return Reservation.objects.create(
            pool=pool,
            user=user,
        )
```

Benefits:

- easier testing,
- reusable from HTTP, admin, commands, and background jobs,
- transaction boundary is explicit,
- business rules stay out of views.

## 8. Use database constraints too

Application code is not enough for every invariant.

Example:

```python
from django.db import models
from django.db.models import Q


class InventoryItem(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="quantity_non_negative",
            )
        ]
```

Now the database itself refuses negative quantities.

Use both layers:

- application/service logic for clear business behavior,
- database constraints for final integrity protection.

## 9. F() expressions for atomic counters

For simple arithmetic updates, `F()` expressions can avoid read-modify-write races.

```python
from django.db.models import F


DevicePool.objects.filter(
    pk=pool_id,
    available__gt=0,
).update(
    available=F("available") - 1
)
```

Check affected rows:

```python
updated = (
    DevicePool.objects
    .filter(
        pk=pool_id,
        available__gt=0,
    )
    .update(
        available=F("available") - 1
    )
)

if updated == 0:
    raise NoAvailability()
```

This is efficient when the whole operation is a single conditional update.

Use row locking when several related checks or writes must stay consistent together.

## 10. When to use F() and when select_for_update()

Use `F()` when:

- one row changes,
- the update can be expressed directly in SQL,
- no complex branching is required,
- you only need to know whether the update succeeded.

Use `select_for_update()` when:

- several rows must change together,
- you must inspect state before deciding,
- several invariants are involved,
- you need to create related records in the same transaction,
- workflow transitions must be serialized.

## 11. Workflow state transitions

Example model:

```python
class Approval(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
```

Unsafe transition:

```python
approval = Approval.objects.get(pk=pk)

if approval.status != "pending":
    raise ValueError("Already processed")

approval.status = "approved"
approval.save()
```

Two administrators could process the same row.

Safer:

```python
from django.db import transaction


def approve(pk):
    with transaction.atomic():
        approval = (
            Approval.objects
            .select_for_update()
            .get(pk=pk)
        )

        if approval.status != "pending":
            raise ValueError(
                "Already processed"
            )

        approval.status = "approved"
        approval.save(
            update_fields=["status"]
        )
```

## 12. nowait=True

Sometimes waiting for a lock is undesirable.

```python
with transaction.atomic():
    row = (
        Job.objects
        .select_for_update(nowait=True)
        .get(pk=job_id)
    )
```

If another transaction already owns the lock, the database raises an error immediately.

Useful for:

- interactive APIs where long waits are unacceptable,
- worker coordination,
- administrative operations that should fail fast.

Catch only the specific database exception you expect.

## 13. skip_locked=True

Workers can use `skip_locked=True` to claim different jobs without waiting on each other.

```python
from django.db import transaction


def claim_next_job():
    with transaction.atomic():
        job = (
            Job.objects
            .select_for_update(
                skip_locked=True
            )
            .filter(status="pending")
            .order_by("created_at")
            .first()
        )

        if job is None:
            return None

        job.status = "running"
        job.save(
            update_fields=["status"]
        )

        return job
```

Multiple workers can call this concurrently and receive different unlocked jobs.

This is a useful pattern for small database-backed queues.

## 14. Keep transactions short

Do not do slow external work while holding database locks.

Bad:

```python
with transaction.atomic():
    order = (
        Order.objects
        .select_for_update()
        .get(pk=order_id)
    )

    response = requests.post(
        external_url,
        json={...},
        timeout=30,
    )

    order.status = "sent"
    order.save()
```

The database row stays locked during the network call.

Prefer:

1. validate and mark state quickly,
2. commit,
3. call the external service,
4. store the result in a separate short transaction.

## 15. transaction.on_commit()

Sometimes external work should happen only if the transaction succeeds.

```python
from django.db import transaction


with transaction.atomic():
    order = Order.objects.create(
        status="created"
    )

    transaction.on_commit(
        lambda: send_order_created_event(
            order.id
        )
    )
```

If the transaction rolls back, the callback is not executed.

Useful for:

- queueing background jobs,
- sending notifications,
- invalidating cache,
- publishing events.

## 16. Nested atomic blocks

Django supports nested `atomic()` blocks using savepoints.

```python
with transaction.atomic():
    create_parent()

    try:
        with transaction.atomic():
            create_optional_child()
    except IntegrityError:
        handle_optional_failure()

    finalize_parent()
```

The inner block can roll back to its savepoint while the outer transaction continues.

Do not overuse nested transactions because they can make failure behavior difficult to reason about.

## 17. Deadlocks

Locks can create deadlocks when transactions acquire rows in different orders.

Example:

```text
Transaction A locks row 1
Transaction B locks row 2
Transaction A waits for row 2
Transaction B waits for row 1
```

Reduce risk by locking resources in a consistent order.

Good pattern:

```python
ids = sorted(
    [source_id, target_id]
)

with transaction.atomic():
    accounts = list(
        Account.objects
        .select_for_update()
        .filter(id__in=ids)
        .order_by("id")
    )
```

All transactions use the same lock ordering.

## 18. Retrying deadlocks carefully

Some databases abort one transaction when a deadlock occurs.

A bounded retry can be reasonable if:

- the operation is transactionally safe,
- the exception is specifically identified as retryable,
- attempts are limited,
- backoff is used.

Do not retry every `DatabaseError`.

Pseudo-pattern:

```python
for attempt in range(3):
    try:
        with transaction.atomic():
            perform_transfer()
        break
    except RetryableDeadlockError:
        if attempt == 2:
            raise

        time.sleep(
            0.05 * (2 ** attempt)
        )
```

## 19. Testing transaction behavior

Ordinary `TestCase` wraps tests in transactions and can hide locking behavior.

For concurrency-sensitive tests, consider `TransactionTestCase`.

```python
from django.test import TransactionTestCase


class ReservationConcurrencyTests(
    TransactionTestCase
):
    reset_sequences = True

    def test_pool_never_becomes_negative(self):
        ...
```

For realistic concurrency tests, run operations from separate database connections/threads and assert the final invariant.

## 20. Example invariant test

Even without a fully concurrent test, test the business invariant.

```python
def test_reservation_fails_when_empty(
    db,
    user,
):
    pool = DevicePool.objects.create(
        name="Lab",
        available=0,
    )

    with pytest.raises(NoAvailability):
        reserve_device(
            pool_id=pool.id,
            user=user,
        )

    pool.refresh_from_db()

    assert pool.available == 0
```

## 21. Unique constraints for duplicate prevention

If an operation must happen only once per user/resource, enforce that in the schema.

```python
class Reservation(models.Model):
    pool = models.ForeignKey(
        DevicePool,
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["pool", "user"],
                name="one_reservation_per_user_pool",
            )
        ]
```

Even if two requests race, the database protects the invariant.

Application code should still catch and translate `IntegrityError` into a meaningful domain error.

## 22. Common mistakes

### Transaction without a lock

```python
with transaction.atomic():
    row = Counter.objects.get(pk=1)
    row.value += 1
    row.save()
```

Two transactions can still read the same value.

### Lock outside atomic()

`select_for_update()` without a transaction does not provide the intended protection.

### Holding locks during HTTP calls

This increases contention and timeout risk.

### Locking too many rows

Large lock scopes reduce concurrency.

### Assuming application validation is enough

Database constraints should protect critical invariants.

### Retrying all database errors

Only retry errors known to be transient.

## 23. Practical decision guide

Use plain `transaction.atomic()` when:

- several writes must succeed or fail together.

Add `select_for_update()` when:

- concurrent requests may modify the same rows,
- a decision depends on current row state.

Use `F()` when:

- a simple numeric or field update can be done atomically in SQL.

Add database constraints when:

- the invariant must remain true regardless of application bugs.

Use `transaction.on_commit()` when:

- external side effects should happen only after a successful commit.

Use `skip_locked=True` when:

- several workers claim independent pending rows.

## 24. Verification checklist

Before considering a concurrency-sensitive feature complete, verify:

- transaction boundaries are explicit,
- locks are acquired only where needed,
- lock order is deterministic,
- transactions are short,
- external network calls do not run while locks are held,
- database constraints protect critical invariants,
- duplicate operations are prevented,
- concurrency behavior is tested,
- deadlock handling is bounded and selective,
- failures are converted into clear domain errors.

The goal is not to lock everything. The goal is to protect the smallest critical section that must remain consistent while allowing unrelated work to proceed concurrently.
