# 04 — Create tasks with POST

This step adds the first write operation to the Tasks API. The request body is validated by Pydantic before application code receives it.

## API code

```python
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI(title="Tasks API")

class TaskCreate(BaseModel):
    title: str

class Task(TaskCreate):
    id: int
    done: bool = False

tasks: list[Task] = []

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate):
    task = Task(id=len(tasks) + 1, title=payload.title)
    tasks.append(task)
    return task
```

## Test the contract

Start `uvicorn main:app --reload`, open `/docs`, and send:

```json
{"title": "Prepare computer lab"}
```

The endpoint should return HTTP 201 and a task containing an assigned `id` and `done: false`. Try an invalid body too: FastAPI should reject it before `create_task` runs.

## Minimal Vue call

```js
const response = await fetch("/tasks", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({title: newTitle.value})
})
const created = await response.json()
tasks.value.push(created)
```

## Exercise

Reject titles containing only whitespace. Then add a second test that creates two tasks and checks that their IDs differ.

## Next step

Lesson 05 separates storage from route handling so the API can later move from an in-memory list to a database without rewriting the Vue client.