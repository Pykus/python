# FastAPI + Vue: health endpoint contract

A small production-oriented exercise: expose `GET /health` from FastAPI and consume it from Vue without coupling the UI to backend internals.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get('/health')
def health():
    return {'status': 'ok'}
```

In Vue, treat any non-2xx response as unavailable and show a short status message. Keep the endpoint read-only, fast and dependency-light so it can be used by monitoring as well as the UI.

Next exercise: add a typed response model and a frontend timeout.