from fastapi.testclient import TestClient

from backend import app

client = TestClient(app)


def test_create_device_returns_validated_payload() -> None:
    response = client.post(
        "/api/devices",
        json={
            "name": "host-a",
            "room": "Lab-1",
            "enabled": True,
            "note": "Synthetic test device",
        },
    )

    assert response.status_code == 201
    assert response.json()["device"]["name"] == "host-a"


def test_validation_errors_are_field_oriented() -> None:
    response = client.post(
        "/api/devices",
        json={
            "name": "!",
            "room": "",
            "enabled": True,
        },
    )

    assert response.status_code == 422
    errors = {item["field"]: item["message"] for item in response.json()["errors"]}
    assert "name" in errors
    assert "room" in errors
