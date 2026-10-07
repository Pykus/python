# Reliable batch processing in Python

Batch jobs need stronger guarantees than a simple loop. A production job should be restartable, observable, bounded in resource use, and safe after partial failure. This pattern fits file conversions, inventory enrichment, report generation, and scheduled imports.

## When to use it
Use checkpointing when a job contains many independent items and rerunning successful work is expensive. Do not use this pattern when the whole operation must be atomic; use a database transaction or transactional queue instead.

## Restartable worker
Persist a stable item key only after successful processing. Write state atomically so interruption cannot leave a truncated checkpoint.

```python
from pathlib import Path
import json, os, tempfile

STATE = Path("batch-state.json")

def load_done():
    if not STATE.exists():
        return set()
    return set(json.loads(STATE.read_text())["done"])

def save_done(done):
    payload = json.dumps({"done": sorted(done)}, indent=2)
    fd, tmp = tempfile.mkstemp(dir=STATE.parent, text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE)

def process(item):
    print("processing", item)

done = load_done()
for item in ["a", "b", "c"]:
    if item in done:
        continue
    process(item)
    done.add(item)
    save_done(done)
```

## Idempotency
A checkpoint cannot protect an operation that succeeded remotely but stopped before state was saved. Prefer idempotent APIs, unique request keys, or database upserts keyed by the source identifier. For file output, write a temporary file, validate it, and rename it into place.

## Retries
Retry only transient failures and cap both attempt count and total duration. Exponential backoff with jitter prevents many workers from retrying at once. Validation failures should be recorded and quarantined rather than retried indefinitely.

## Observability
Log item ID, attempt number, elapsed time, result, and exception class. Keep counters for succeeded, skipped, retried, and failed items. Define an explicit failure threshold and return a non-zero exit status when it is exceeded.

## Resource bounds
Stream large input rather than loading everything into memory. Limit concurrency with a fixed worker pool. Set network timeouts. Use context managers for files and connections so failures do not leak resources.

## Common failures
Do not use list position as a checkpoint key because input ordering can change. Do not save completion before the side effect. Do not catch every exception without recording context. Prevent concurrent runs from sharing one state file unless locking is implemented.

## Verification
Run once and verify every item completes. Run again and verify completed items are skipped. Inject a failure in the middle and confirm the next run resumes correctly. Interrupt during checkpoint persistence and verify the state remains valid. Finally, deliberately execute one item twice and confirm the external effect remains single through idempotency.

Reliable batch processing is mainly about predictable recovery. Checkpoints, idempotent effects, bounded retries, resource limits, and measurable outcomes turn a fragile script into an operational tool.