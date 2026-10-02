# Bounded retry with exponential backoff

Retry only operations that can safely be repeated, and cap attempts and delay.

```python
for attempt in range(4):
    try:
        return operation()
    except TimeoutError:
        if attempt == 3:
            raise
        time.sleep(min(0.25 * (2 ** attempt), 2.0))
```

Do not retry permanent validation or permission errors. Production implementations should add jitter and structured logging.
