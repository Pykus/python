# Bounded retry with exponential backoff

Retries are useful when a failure is likely to be temporary: a short network interruption, a busy API, a transient database connection problem, or a remote service returning a retryable status.

They are dangerous when used blindly. A retry loop can turn one failing request into a request storm, repeat a non-idempotent operation, hide a permanent configuration error, or make an outage harder to diagnose.

## What problem this solves

The tool is for operations that are expected to work most of the time but may fail briefly because of conditions outside the program. Typical examples are HTTP calls, health checks, remote administration APIs, object-storage downloads, temporary database connection failures, or waiting for a freshly started service.

The core policy is:

- retry only selected transient failures,
- stop after a bounded number of attempts,
- wait longer after each failure,
- cap the maximum delay,
- add jitter when many clients may retry together,
- log every retry,
- do not blindly repeat destructive or non-idempotent actions.

## Basic implementation

~~~python
import time


def run_with_retry(operation, attempts=4, base_delay=0.25, max_delay=2.0):
    for attempt in range(attempts):
        try:
            return operation()
        except TimeoutError:
            if attempt == attempts - 1:
                raise

            delay = min(base_delay * (2 ** attempt), max_delay)
            time.sleep(delay)
~~~

For four attempts the waits are approximately 0.25 s, 0.50 s, and 1.00 s. If the fourth attempt fails, the exception is raised.

## Why exponential backoff

A fixed retry interval can make a bad situation worse. If 500 clients all retry every 100 ms, the service receives another burst while it is already overloaded.

Exponential backoff spreads the load:

~~~text
0.25 s
0.50 s
1.00 s
2.00 s
2.00 s
...
~~~

The maximum delay prevents the wait from growing without limit.

## Add jitter

Even exponential backoff can keep many clients synchronized. Jitter randomizes the delay.

~~~python
import random


def retry_delay(attempt, base=0.25, maximum=5.0):
    upper = min(base * (2 ** attempt), maximum)
    return random.uniform(0, upper)
~~~

## Example 1: HTTP GET

GET requests are usually good retry candidates because they should not create new state.

~~~python
import random
import time
import requests

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def get_json(url, attempts=5):
    for attempt in range(attempts):
        try:
            response = requests.get(url, timeout=5)

            if response.status_code not in RETRYABLE_STATUS:
                response.raise_for_status()
                return response.json()

            if attempt == attempts - 1:
                response.raise_for_status()

        except (requests.Timeout, requests.ConnectionError):
            if attempt == attempts - 1:
                raise

        delay = random.uniform(0, min(0.5 * (2 ** attempt), 8.0))
        time.sleep(delay)
~~~

This retries connection failures, timeouts, and selected temporary HTTP failures. A 401 Unauthorized should normally fail immediately because another retry will not fix credentials.

## Example 2: respect Retry-After

Rate-limited APIs may tell the client exactly how long to wait.

~~~python
import time
import requests


def get_rate_limited(url, attempts=5):
    for attempt in range(attempts):
        response = requests.get(url, timeout=5)

        if response.ok:
            return response

        if response.status_code != 429:
            response.raise_for_status()

        if attempt == attempts - 1:
            response.raise_for_status()

        retry_after = response.headers.get('Retry-After')
        delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 8)
        time.sleep(delay)
~~~

## Example 3: wait for a service after deployment

A process may be running before its HTTP endpoint is ready.

~~~python
import time
import requests


def wait_until_ready(url, attempts=8):
    for attempt in range(attempts):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass

        if attempt == attempts - 1:
            return False

        time.sleep(min(0.5 * (2 ** attempt), 5.0))

    return False
~~~

Usage:

~~~python
if not wait_until_ready('http://127.0.0.1:8000/health/ready'):
    raise RuntimeError('Service did not become ready')
~~~

This pattern is useful in deployment scripts, smoke tests, container startup checks, and local development tooling.

## Example 4: temporary database reconnect

~~~python
import time
import psycopg


def connect_database(dsn, attempts=5):
    last_error = None

    for attempt in range(attempts):
        try:
            return psycopg.connect(dsn, connect_timeout=3)
        except psycopg.OperationalError as exc:
            last_error = exc

            if attempt == attempts - 1:
                break

            time.sleep(min(0.5 * (2 ** attempt), 4.0))

    raise last_error
~~~

Retry an operational connection failure. Do not retry a SQL syntax error or a permanently invalid DSN.

## Example 5: safer file download

Write to a temporary file and replace the destination only after a complete download.

~~~python
from pathlib import Path
import os
import time
import requests


def download_file(url, destination, attempts=4):
    destination = Path(destination)
    temporary = destination.with_suffix(destination.suffix + '.part')

    for attempt in range(attempts):
        try:
            with requests.get(url, timeout=10, stream=True) as response:
                response.raise_for_status()
                with temporary.open('wb') as handle:
                    for chunk in response.iter_content(128 * 1024):
                        if chunk:
                            handle.write(chunk)

            os.replace(temporary, destination)
            return destination

        except requests.RequestException:
            temporary.unlink(missing_ok=True)
            if attempt == attempts - 1:
                raise
            time.sleep(min(1 * (2 ** attempt), 8))
~~~

## Idempotency matters

Retries are safest for operations that can be repeated without changing the final result. GET is usually safe. POST may not be.

If a payment, ticket creation, or order request succeeds on the server but the response is lost, a blind retry can create a duplicate.

When the API supports idempotency keys, reuse the same key across retries:

~~~python
import uuid
import requests

key = str(uuid.uuid4())

response = requests.post(
    'https://api.example.test/orders',
    headers={'Idempotency-Key': key},
    json={'product_id': 123, 'quantity': 1},
    timeout=5,
)
~~~

## Retry the observation, not the destructive action

A particularly useful operations pattern is to issue a restart once and retry only the status check.

~~~python
restart_agent(host_id)

for attempt in range(6):
    if check_agent_online(host_id):
        break

    if attempt == 5:
        raise RuntimeError('Agent did not return online')

    time.sleep(min(1 * (2 ** attempt), 8))
~~~

This avoids sending the restart command multiple times.

## Logging and observability

Retries without logs hide instability. Record at least:

- operation name,
- attempt number,
- delay,
- exception type,
- HTTP status code when relevant,
- target service,
- total elapsed time.

Never log authorization headers, passwords, API keys, or secrets.

~~~python
logger.warning(
    'temporary failure; retrying',
    extra={
        'attempt': attempt + 1,
        'max_attempts': attempts,
        'delay_seconds': delay,
        'error': str(exc),
    },
)
~~~

## Total time budget

Attempt count alone may not be enough if each network call can block for several seconds.

~~~python
import time


def retry_with_deadline(operation, attempts=5, deadline_seconds=10):
    started = time.monotonic()

    for attempt in range(attempts):
        try:
            return operation()
        except TimeoutError:
            elapsed = time.monotonic() - started

            if attempt == attempts - 1 or elapsed >= deadline_seconds:
                raise

            delay = min(0.25 * (2 ** attempt), 2.0)
            remaining = deadline_seconds - elapsed
            time.sleep(min(delay, remaining))
~~~

## Common mistakes

1. Infinite retries with while True.
2. Retrying immediately with no delay.
3. Catching Exception and retrying programming errors.
4. Blindly retrying POST or other write operations.
5. Ignoring Retry-After.
6. No logging.
7. No overall time budget.

## Practical decision checklist

Before adding retry logic, answer:

1. Is the failure genuinely temporary?
2. Is the operation safe to repeat?
3. Which exact exceptions or status codes are retryable?
4. How many attempts are acceptable?
5. What is the maximum delay?
6. Should jitter be added?
7. Is there a total deadline?
8. Will every retry be logged?
9. Does the server provide Retry-After?
10. Could the retry create duplicate state?

The goal is not to hide failures. The goal is to survive transient failures without making the original problem worse.