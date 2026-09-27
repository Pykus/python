from fastapi.testclient import TestClient
from main import app, tasks

client = TestClient(app)

def setup_function():
    tasks.clear()

def test_create_task_returns_201_and_resource():
    response = client.post("/tasks", json={"title": " Prepare computer lab "})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "title": "Prepare computer lab", "done": False}

def test_blank_title_is_rejected():
    response = client.post("/tasks", json={"title": "   "})
    assert response.status_code == 422

def test_ids_are_distinct():
    first = client.post("/tasks", json={"title": "One"}).json()
    second = client.post("/tasks", json={"title": "Two"}).json()
    assert first["id"] != second["id"]
