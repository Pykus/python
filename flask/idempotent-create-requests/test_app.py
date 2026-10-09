import sqlite3
from app import create_app


def post(client, key, item="Keyboard", amount=12900):
    return client.post(
        "/orders",
        json={"item": item, "amount_cents": amount},
        headers={"Idempotency-Key": key},
    )


def test_retries_do_not_create_duplicate_orders(tmp_path):
    path = str(tmp_path / "orders.sqlite3")
    client = create_app(path).test_client()
    first = post(client, "order-0001")
    second = post(client, "order-0001")
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json["id"] == second.json["id"]
    assert second.json["replayed"] is True
    assert second.headers["Idempotency-Replayed"] == "true"
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1


def test_key_cannot_be_reused_for_different_order(tmp_path):
    client = create_app(str(tmp_path / "orders.sqlite3")).test_client()
    assert post(client, "order-0002").status_code == 201
    assert post(client, "order-0002", amount=9900).status_code == 409


def test_different_keys_create_different_orders(tmp_path):
    client = create_app(str(tmp_path / "orders.sqlite3")).test_client()
    a = post(client, "order-0003")
    b = post(client, "order-0004")
    assert a.status_code == b.status_code == 201
    assert a.json["id"] != b.json["id"]


def test_invalid_request_is_rejected_before_transaction(tmp_path):
    client = create_app(str(tmp_path / "orders.sqlite3")).test_client()
    assert post(client, "bad").status_code == 400
    assert post(client, "order-0005", amount=-1).status_code == 400
    assert post(client, "order-0005").status_code == 201


def test_retry_after_new_app_instance(tmp_path):
    path = str(tmp_path / "orders.sqlite3")
    first = post(create_app(path).test_client(), "order-0006")
    second = post(create_app(path).test_client(), "order-0006")
    assert first.json["id"] == second.json["id"]
    assert second.status_code == 200
