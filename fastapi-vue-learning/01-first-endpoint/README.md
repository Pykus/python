# 01 — First FastAPI endpoint

This is the first step of the FastAPI + Vue learning project.

The working application code lives in the parent directory in `main.py`. At this stage the goal is deliberately small: create a FastAPI application and expose one JSON endpoint.

## Code

```python
from fastapi import FastAPI

app = FastAPI(title="Tasks API")

tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Connect Vue", "done": False},
]


@app.get("/tasks")
def list_tasks():
    return tasks
```

## Run

```bash
python -m pip install fastapi "uvicorn[standard]"
uvicorn main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/tasks
http://127.0.0.1:8000/docs
```

## What to notice

- `FastAPI()` creates the application.
- `@app.get("/tasks")` registers a GET endpoint.
- Returning normal Python lists and dictionaries produces JSON automatically.
- The automatic OpenAPI documentation is available at `/docs`.

## Exercise

Add a third task to the list and verify that it appears both in `/tasks` and in the response shown from `/docs`.
