# Flask: small admin health endpoint

A minimal pattern for an internal application that exposes a read-only health endpoint.

```python
from datetime import datetime, timezone
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "admin-demo",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    })
```

## Test

```python
def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["service"] == "admin-demo"
```

## Why this is useful

Monitoring systems can call one stable endpoint instead of scraping HTML. Keep the endpoint read-only and do not expose secrets, hostnames, tokens, or internal topology.