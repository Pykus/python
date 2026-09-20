# FastAPI + Vue learning

Small step-by-step project used to learn a FastAPI backend and, next, a Vue 3 frontend.

## Day 1 — first API endpoint

The backend exposes one route:

```text
GET /tasks
```

Run it:

```bash
python -m pip install fastapi "uvicorn[standard]"
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/tasks` or the interactive docs at `http://127.0.0.1:8000/docs`.

Today the goal is only routing and returning JSON. The next step is a Pydantic response model, followed by a tiny Vue component that fetches the task list.
