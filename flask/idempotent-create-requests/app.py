"""A small, durable example of idempotent order creation with Flask."""
import hashlib
import json
import os
import re
import sqlite3

from flask import Flask, jsonify, request


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE_PATH"] = database_path or os.environ.get(
        "DATABASE_PATH", "orders.sqlite3"
    )
    with sqlite3.connect(app.config["DATABASE_PATH"]) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS orders ("
            "id INTEGER PRIMARY KEY, item TEXT NOT NULL, amount_cents INTEGER NOT NULL)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS idempotency ("
            "key TEXT PRIMARY KEY, request_hash TEXT NOT NULL, order_id INTEGER NOT NULL)"
        )

    @app.post("/orders")
    def create_order():
        key = request.headers.get("Idempotency-Key", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", key):
            return jsonify(error="Invalid Idempotency-Key"), 400

        data = request.get_json(silent=True)
        if not isinstance(data, dict) or set(data) != {"item", "amount_cents"}:
            return jsonify(error="Expected item and amount_cents"), 400
        item, amount = data["item"], data["amount_cents"]
        if (not isinstance(item, str) or not 1 <= len(item.strip()) <= 100
                or type(amount) is not int or not 1 <= amount <= 10_000_000):
            return jsonify(error="Invalid item or amount_cents"), 400

        normalized = {"item": item.strip(), "amount_cents": amount}
        fingerprint = hashlib.sha256(
            json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        db = sqlite3.connect(app.config["DATABASE_PATH"], timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT request_hash, order_id FROM idempotency WHERE key = ?", (key,)
            ).fetchone()
            if previous:
                if previous["request_hash"] != fingerprint:
                    db.rollback()
                    return jsonify(error="Key reused with different payload"), 409
                order_id = previous["order_id"]
                db.commit()
                response = jsonify(id=order_id, replayed=True)
                response.headers["Idempotency-Replayed"] = "true"
                return response, 200

            cursor = db.execute(
                "INSERT INTO orders(item, amount_cents) VALUES (?, ?)",
                (normalized["item"], amount),
            )
            order_id = cursor.lastrowid
            db.execute(
                "INSERT INTO idempotency(key, request_hash, order_id) VALUES (?, ?, ?)",
                (key, fingerprint, order_id),
            )
            db.commit()
            return jsonify(id=order_id, replayed=False), 201
        except sqlite3.Error:
            db.rollback()
            app.logger.exception("Database transaction failed")
            return jsonify(error="Storage temporarily unavailable"), 503
        finally:
            db.close()

    return app


app = create_app()
