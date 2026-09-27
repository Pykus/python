from fastapi import FastAPI, status
from pydantic import BaseModel, field_validator

app = FastAPI(title="Tasks API")

class TaskCreate(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

class Task(TaskCreate):
    id: int
    done: bool = False

tasks: list[Task] = []

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> Task:
    task = Task(id=len(tasks) + 1, title=payload.title)
    tasks.append(task)
    return task
