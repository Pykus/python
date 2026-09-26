# 02 — Pydantic response model

The second step adds a typed response model. The goal is to make the API contract explicit before a Vue frontend starts consuming it.

The current application code is still kept in the parent `main.py`.

## Code

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Tasks API")


class Task(BaseModel):
    id: int
    title: str
    done: bool = False


tasks = [
    Task(id=1, title="Learn FastAPI"),
    Task(id=2, title="Connect Vue"),
]


@app.get("/tasks", response_model=list[Task])
def list_tasks():
    return tasks
```

## What changed

The `Task` model documents the shape of every task returned by the endpoint:

- `id` must be an integer,
- `title` must be text,
- `done` is a boolean and defaults to `False`.

The route now declares:

```python
response_model=list[Task]
```

That gives FastAPI a clear schema for validation and generated documentation.

## Check it

Run the application:

```bash
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` and inspect the documented response schema for `GET /tasks`.

## Exercise

Add an optional `description: str | None = None` field to `Task`, update one task with a description, and inspect the OpenAPI schema again.

## Next step

Lesson 03 adds query-based filtering so the same endpoint can return a subset of the task list.
