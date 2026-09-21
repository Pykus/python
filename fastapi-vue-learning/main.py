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
