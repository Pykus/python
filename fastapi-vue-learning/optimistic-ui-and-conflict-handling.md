# FastAPI + Vue: optimistic UI with safe rollback

A Vue interface feels slow when every button waits for a network round trip before changing the screen. Optimistic UI updates the local state immediately, sends the request in the background, and either confirms the change or rolls it back. It works well for reversible, low-risk actions such as toggling a task, changing a label, or updating a device note.

It is a poor fit for irreversible operations such as deleting backups, issuing payments, or actions whose server-side validation frequently rejects input. In those cases, confirmation from the backend should remain visible before the UI claims success.

## API contract

Assume a task has a version number. The client sends the version it edited, allowing the API to detect stale updates instead of silently overwriting another user's change.

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class TaskPatch(BaseModel):
    done: bool
    expected_version: int

class TaskOut(BaseModel):
    id: int
    title: str
    done: bool
    version: int

tasks = {
    1: {"id": 1, "title": "Check backup", "done": False, "version": 3}
}

@app.patch("/api/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, patch: TaskPatch):
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["version"] != patch.expected_version:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Task changed on the server",
                "current": task,
            },
        )

    task["done"] = patch.done
    task["version"] += 1
    return task
```

In a real application, perform the version check and update atomically in the database. A SQL statement such as `UPDATE ... WHERE id=? AND version=?` followed by a row-count check avoids a race between reading and writing.

## Vue state and optimistic update

```vue
<script setup>
import { ref } from "vue"

const tasks = ref([
  { id: 1, title: "Check backup", done: false, version: 3, saving: false }
])
const error = ref("")

async function toggleTask(task) {
  if (task.saving) return

  const before = { ...task }
  task.done = !task.done
  task.saving = true
  error.value = ""

  try {
    const response = await fetch(`/api/tasks/${task.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        done: task.done,
        expected_version: before.version
      })
    })

    if (!response.ok) {
      const payload = await response.json()
      const failure = new Error("Update failed")
      failure.status = response.status
      failure.payload = payload
      throw failure
    }

    const saved = await response.json()
    Object.assign(task, saved)
  } catch (exc) {
    Object.assign(task, before)

    if (exc.status === 409) {
      const current = exc.payload?.detail?.current
      if (current) Object.assign(task, current)
      error.value = "Task changed elsewhere. Current server state was loaded."
    } else {
      error.value = "Could not save the change. Your previous state was restored."
    }
  } finally {
    task.saving = false
  }
}
</script>

<template>
  <p v-if="error" role="alert">{{ error }}</p>
  <ul>
    <li v-for="task in tasks" :key="task.id">
      <label>
        <input
          type="checkbox"
          :checked="task.done"
          :disabled="task.saving"
          @change="toggleTask(task)"
        />
        {{ task.title }}
        <span v-if="task.saving">Saving…</span>
      </label>
    </li>
  </ul>
</template>
```

Disabling the control while one mutation is pending is the simplest way to prevent multiple in-flight writes from arriving out of order. More advanced interfaces can queue changes, but then each response must be correlated with the mutation that produced it.

## Why rollback must restore more than one field

Saving only `beforeDone` is fragile. A successful response may update version, timestamps, normalized text, or server-calculated fields. Snapshot the relevant object before the optimistic change and replace it with the authoritative response after success.

For larger stores, avoid blindly cloning an entire application state. Keep mutation scope small and use a store action that owns the optimistic state, request, rollback, and error message.

## FastAPI test

```python
from fastapi.testclient import TestClient
from main import app, tasks

client = TestClient(app)

def test_rejects_stale_version():
    tasks[1] = {"id": 1, "title": "Check backup", "done": False, "version": 3}

    ok = client.patch(
        "/api/tasks/1",
        json={"done": True, "expected_version": 3},
    )
    assert ok.status_code == 200
    assert ok.json()["version"] == 4

    stale = client.patch(
        "/api/tasks/1",
        json={"done": False, "expected_version": 3},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["current"]["version"] == 4
```

## Failure scenarios to test

Test HTTP 422 for malformed payloads, 404 for deleted records, 409 for stale versions, a network timeout, and a 500 response. In the browser, verify that failed requests restore the old checkbox state and expose an accessible error message. Use throttling in browser developer tools to confirm that the optimistic update is visible before the delayed response.

Also test two tabs: load the same version in both, save in the first, then save a conflicting value in the second. The second tab should receive 409 and replace its stale state with the current server representation.

## Common mistakes

Do not treat every non-2xx response as a generic network error; conflicts need different UX from server outages. Do not increment the version only in Vue: the backend owns concurrency. Do not let a late response overwrite a newer local mutation. Do not optimistically display security-sensitive authorization changes before the server accepts them.

For database-backed APIs, version checking must be atomic. Reading the row, comparing in Python, and then writing in a separate query can still lose an update under concurrency.

## Practical takeaway

Optimistic UI is not merely an animation trick. The Vue side needs a reversible local mutation, while FastAPI needs an explicit conflict contract and the persistence layer needs atomic concurrency control. With all three pieces, routine actions feel immediate without silently discarding another user's changes.
