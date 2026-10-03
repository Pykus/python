# Flask request correlation IDs

A request correlation ID gives one HTTP request a stable identifier that can be returned to the client, written to application logs, and forwarded to downstream services.

It is useful when a user reports that an API request failed but many requests were handled at the same time. Instead of searching by timestamp alone, support can search for one request ID and follow the exact request through logs.

## What problem this solves

Without a correlation ID, logs from several requests can be interleaved:

```text
INFO loading user
INFO calling inventory service
ERROR timeout
INFO loading user
INFO response 200
```

With a request ID:

```text
INFO request_id=6e7f... loading user
INFO request_id=6e7f... calling inventory service
ERROR request_id=6e7f... timeout
INFO request_id=102a... loading user
INFO request_id=102a... response 200
```

Now the failing flow can be isolated immediately.

## Minimal Flask implementation

```python
from uuid import uuid4

from flask import Flask, g, request

app = Flask(__name__)


@app.before_request
def assign_request_id():
    incoming = request.headers.get("X-Request-ID")
    g.request_id = incoming or str(uuid4())


@app.after_request
def add_request_id_header(response):
    response.headers["X-Request-ID"] = g.request_id
    return response
```

This preserves an existing ID from an upstream reverse proxy or gateway. If none exists, Flask creates one.

## Validate incoming request IDs

A client-controlled header can contain very long or malformed values. Validate it before putting it into logs.

```python
import re
from uuid import uuid4

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def normalize_request_id(value):
    if value and REQUEST_ID_RE.fullmatch(value):
        return value

    return str(uuid4())
```

Use it in the hook:

```python
@app.before_request
def assign_request_id():
    g.request_id = normalize_request_id(
        request.headers.get("X-Request-ID")
    )
```

This avoids obvious log pollution and unreasonable header sizes.

## Put the ID in logs

A simple helper:

```python
import logging

logger = logging.getLogger(__name__)


def log_info(message, **extra):
    logger.info(
        message,
        extra={
            "request_id": getattr(g, "request_id", None),
            **extra,
        },
    )
```

Usage:

```python
@app.get("/api/assets/<asset_id>")
def asset(asset_id):
    log_info(
        "loading asset",
        asset_id=asset_id,
    )

    return {
        "asset_id": asset_id,
    }
```

## Better: logging filter

If every log call must manually add the request ID, someone will eventually forget. A logging filter can inject it automatically.

```python
import logging

from flask import g, has_request_context


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if has_request_context():
            record.request_id = getattr(
                g,
                "request_id",
                "-",
            )
        else:
            record.request_id = "-"

        return True
```

Configure the formatter:

```python
handler = logging.StreamHandler()

handler.addFilter(
    RequestIdFilter()
)

handler.setFormatter(
    logging.Formatter(
        "%(asctime)s %(levelname)s "
        "request_id=%(request_id)s "
        "%(message)s"
    )
)

app.logger.handlers.clear()
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
```

Now this:

```python
app.logger.info(
    "starting inventory lookup"
)
```

automatically includes the current request ID.

## Propagate the same ID downstream

The largest benefit appears when several services participate in one request.

```python
import requests


def call_inventory_service(asset_id):
    response = requests.get(
        f"http://inventory-api.local/assets/{asset_id}",
        headers={
            "X-Request-ID": g.request_id,
        },
        timeout=3,
    )

    response.raise_for_status()
    return response.json()
```

If the downstream service also logs X-Request-ID, the same identifier connects both services.

## Example multi-service flow

```text
browser
  |
  | X-Request-ID: 8c9a...
  v
Flask API
  | log request_id=8c9a...
  |
  | X-Request-ID: 8c9a...
  v
inventory service
  | log request_id=8c9a...
  v
database / another service
```

This is useful even before adopting a full distributed tracing platform.

## Return the ID in error responses

When a request fails, returning the same ID gives the user or support team something concrete to report.

```python
from flask import jsonify


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    app.logger.exception(
        "unhandled request error"
    )

    return (
        jsonify(
            error="internal_server_error",
            request_id=g.request_id,
        ),
        500,
    )
```

A support ticket can then include:

```text
Request ID: 8c9a93d4-...
```

That is much more precise than only a screenshot or approximate time.

## Example: request timing

Correlation IDs become even more useful when combined with request duration.

```python
import time


@app.before_request
def start_request():
    g.request_started = time.monotonic()

    incoming = request.headers.get(
        "X-Request-ID"
    )

    g.request_id = normalize_request_id(
        incoming
    )


@app.after_request
def finish_request(response):
    elapsed_ms = (
        time.monotonic()
        - g.request_started
    ) * 1000

    app.logger.info(
        "request completed",
        extra={
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": round(
                elapsed_ms,
                2,
            ),
        },
    )

    response.headers[
        "X-Request-ID"
    ] = g.request_id

    return response
```

Now one log record can answer:

- which request,
- which path,
- which status,
- how long it took.

## Example: structured JSON logging

For log aggregation systems, JSON is often more convenient than plain text.

```python
import json
import logging


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": getattr(
                record,
                "request_id",
                "-",
            ),
        }

        return json.dumps(payload)


handler = logging.StreamHandler()
handler.addFilter(RequestIdFilter())
handler.setFormatter(JsonFormatter())
```

Example output:

```json
{
  "level": "INFO",
  "message": "request completed",
  "request_id": "8c9a93d4-..."
}
```

This is easier to search in Loki, Elasticsearch, OpenSearch, Splunk, or similar systems.

## Correlation IDs in background jobs

Flask's g object exists only inside the request context.

If work is queued to Celery, RQ, or another worker, copy the request ID into the job payload.

```python
job = {
    "asset_id": asset_id,
    "request_id": g.request_id,
}

queue.enqueue(
    process_asset,
    job,
)
```

Worker:

```python
def process_asset(job):
    logger.info(
        "processing queued asset",
        extra={
            "request_id":
                job["request_id"],
        },
    )
```

This preserves the diagnostic link after the HTTP request itself has ended.

## Reverse proxy considerations

An upstream component such as Nginx, a load balancer, or API gateway may already generate a request ID.

In that case Flask should normally preserve the trusted upstream value instead of replacing it.

However, trust should be explicit. If Flask is directly reachable by untrusted clients, accepting arbitrary X-Request-ID values may allow log pollution.

A common design is:

1. gateway removes or validates any client-supplied ID,
2. gateway generates an ID when needed,
3. Flask trusts the gateway-provided value.

## Request ID is not authentication

A request ID is only a tracing value.

Do not use it as:

- a session ID,
- a password-reset token,
- proof of user identity,
- an authorization decision,
- a CSRF token.

Clients may know or even supply the value. It must never grant access.

## Request ID versus trace ID

Modern observability systems often use trace IDs and span IDs.

A simple model:

```text
request_id = user/support-facing correlation value
trace_id   = distributed trace identifier
span_id    = one operation inside a trace
```

If OpenTelemetry is already available, use its trace context for distributed tracing. A request ID can still be useful in user-facing error messages and support workflows.

## Testing the implementation

A basic Flask test verifies that an ID is generated and returned.

```python
def test_request_id_is_generated(client):
    response = client.get(
        "/health"
    )

    request_id = response.headers.get(
        "X-Request-ID"
    )

    assert request_id
```

Verify preservation of a valid incoming ID:

```python
def test_request_id_is_preserved(client):
    response = client.get(
        "/health",
        headers={
            "X-Request-ID":
                "test-request-123",
        },
    )

    assert (
        response.headers[
            "X-Request-ID"
        ]
        == "test-request-123"
    )
```

Verify rejection of malformed input:

```python
def test_invalid_request_id_is_replaced(client):
    response = client.get(
        "/health",
        headers={
            "X-Request-ID":
                "bad value with spaces",
        },
    )

    assert (
        response.headers[
            "X-Request-ID"
        ]
        != "bad value with spaces"
    )
```

## Common mistakes

1. Generating a new ID in every downstream service instead of forwarding the original one.
2. Forgetting to return the ID to the caller.
3. Logging the ID only on errors instead of on all relevant request logs.
4. Trusting arbitrary very long client values.
5. Treating the ID as authentication.
6. Losing the ID when work moves to a background queue.
7. Mixing several header names across services.
8. Adding request IDs but not making logs searchable by that field.

## Practical deployment checklist

Before calling the implementation complete, verify:

- every inbound request has an ID,
- the response includes the same ID,
- application logs include it,
- error responses include it where appropriate,
- downstream requests forward it,
- background jobs preserve it,
- malformed incoming IDs are rejected or replaced,
- log aggregation indexes the field,
- secrets are never placed inside the ID.

A correlation ID is a small feature, but it becomes extremely valuable when diagnosing failures across multiple services.
