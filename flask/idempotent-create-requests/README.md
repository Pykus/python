# Idempotent HTTP POST in Flask: retry-safe order creation

A client sends POST /orders, but its connection drops after the server commits an order and before the response arrives. Retrying an ordinary POST can create a duplicate. An idempotency key lets the client identify a retry as the same operation. The server stores the key alongside the result and returns the original order identifier on identical requests.

Use this for administrative APIs, internal tools, and forms where a repeated side effect would be harmful. Do not use it as a substitute for authorization or a payment provider's own idempotency controls. For large multi-instance deployments, use a shared transactional database rather than a local SQLite file.

## Contract and data model

The client generates one fresh key per logical operation and keeps it unchanged for every retry. In this example the header `Idempotency-Key` accepts 8–100 URL-safe characters. The JSON body has exactly two fields: `item` (nonempty string) and `amount_cents` (positive integer). Storing prices as integer cents avoids binary floating-point errors.

| Condition | HTTP status | Effect |
| --- | --- | --- |
| New key, valid payload | 201 | Insert one order and persist key/fingerprint |
| Same key, same normalized payload | 200 | Return original order ID; replay header true |
| Same key, different payload | 409 | Conflict, no new order |
| Invalid key or JSON | 400 | Reject before transaction |
| Storage failure | 503 | Roll back and allow client retry |

The normalized payload is serialized with sorted JSON keys and hashed with SHA-256. This means harmless changes in JSON key ordering do not change the operation identity. The hash is not authentication. For multi-tenant applications, scope each key to the authenticated tenant and operation, and check authorization before revealing an existing order.

The example includes `app.py`, `test_app.py`, and `requirements.txt`. It uses SQLite to keep the demonstration self-contained and durable across process restarts. A local database file is appropriate for a small application or teaching lab, not a multi-server cluster.

## Installation and full request example

From this directory, create an environment and install the two dependencies:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q test_app.py
python -m flask --app app run --port 5000
```

Send a request from another terminal:

```bash
curl -i -X POST http://127.0.0.1:5000/orders \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-2026-0001" \
  -d '{"item":"Keyboard","amount_cents":12900}'
```

The first response is HTTP 201 with `{"id":1,"replayed":false}`. Repeat the exact command: HTTP 200 returns the same ID with `replayed:true` and an `Idempotency-Replayed: true` header. Change the amount to 9900 while keeping the key: HTTP 409. Change only the key: a new order is created. In a browser, create the key when the user begins one submission and preserve it across retry clicks until success or explicit cancellation. Never generate a new key simply because a network timeout occurred.

Set the `DATABASE_PATH` environment variable to a persistent writable location if the working directory may change. The default is `orders.sqlite3` in the current directory. Keep database files and credentials out of source control.

## Why a single transaction is essential

A naive implementation checks the key, inserts the order, commits, then saves the key in another commit. A crash between these writes leaves an order without a retry record. A retry creates a duplicate. Two concurrent requests may also both pass a non-atomic "key not found" check.

The implementation starts `BEGIN IMMEDIATE` before looking up the key. SQLite reserves the write transaction, then the key lookup, order insert, key insert and commit form one atomic operation. The primary-key constraint protects the idempotency table as well. If the process crashes before commit, neither insert survives; if it crashes after commit, both survive. SQLite serializes writers, which is safe for modest workloads but may be slow under high contention. The connection timeout limits lock waiting. A production PostgreSQL design would use a unique key and a transaction with an explicit state machine for in-progress operations.

## Three practical applications

**School equipment requests:** a teacher submits a checkout request but the browser times out. Repeating the form with the same key retrieves the original request instead of producing two tickets.

**Queue consumers:** a message broker redelivers a create operation after an acknowledgment failure. The worker stores or derives a stable operation key and processes the business effect only once.

**Mobile connections:** a phone sends a request over unreliable Wi-Fi. The app persists the pending operation key locally and retries the identical payload when connectivity returns. The key must not change between attempts.

## Common pitfalls and boundaries

This sample does not expire keys. In production, define retention based on the maximum retry horizon and do not delete records while old requests can still be retried. It does not authenticate callers; implement authentication, authorization, and tenant-scoped keys. It does not coordinate external side effects such as sending email or charging cards; use a transactional outbox and the external provider's idempotency mechanism. SQLite is file-local and can lock under write contention; horizontally scaled services should use a shared transactional database. A Python boolean is technically an integer subclass, so validation explicitly rejects it as an amount. Never log secret headers or sensitive payloads.

## Verification and practical conclusion

Five automated pytest cases check repeated requests, changed payload conflicts, different keys, invalid inputs, and replay after constructing a new app instance. For production, add a concurrency test with simultaneous identical requests, database restore tests, and monitoring of HTTP 201, replay 200, conflict 409, and transient 503 responses. Verify both business-row and idempotency-row counts; HTTP responses alone do not prove absence of duplicates.

The core rule is to persist the business side effect and its retry identity atomically, reject key reuse with a different request, and test durability across restarts rather than relying only on a successful first request.
