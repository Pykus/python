from fastapi import FastAPI

app = FastAPI(title="Tasks API")

tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Connect Vue", "done": False},
]


@app.get("/tasks")
def list_tasks():
    return tasks
