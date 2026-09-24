"""Minimal Flask API for a small school-journal side project.

This example demonstrates an application factory, input validation and predictable JSON
responses without depending on a database yet.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from flask import Flask, jsonify, request


@dataclass(slots=True)
class Announcement:
    id: int
    title: str
    body: str


ANNOUNCEMENTS: list[Announcement] = [
    Announcement(id=1, title="Welcome", body="The journal API is running."),
]


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/announcements")
    def list_announcements():
        return jsonify([asdict(item) for item in ANNOUNCEMENTS])

    @app.post("/api/announcements")
    def create_announcement():
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title", "")).strip()
        body = str(payload.get("body", "")).strip()

        if not title or not body:
            return jsonify(error="title and body are required"), 400

        item = Announcement(
            id=max((entry.id for entry in ANNOUNCEMENTS), default=0) + 1,
            title=title,
            body=body,
        )
        ANNOUNCEMENTS.append(item)
        return jsonify(asdict(item)), 201

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
