from __future__ import annotations
from flask import Flask, jsonify

app = Flask(__name__)

class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message

@app.errorhandler(ApiError)
def handle_api_error(exc: ApiError):
    return jsonify(error={"code": exc.code, "message": exc.message}), exc.status

@app.get("/health")
def health():
    return jsonify(ok=True)

@app.get("/device/<name>")
def device(name: str):
    if not name.strip():
        raise ApiError(400, "invalid_name", "Device name is required")
    return jsonify(name=name)
