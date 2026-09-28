from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Device form validation example")


class DeviceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    room: str = Field(min_length=1, max_length=32)
    enabled: bool = True
    note: str | None = Field(default=None, max_length=200)


def _field_from_location(location: tuple[Any, ...]) -> str:
    useful = [str(part) for part in location if part not in {"body", "query", "path"}]
    return ".".join(useful) if useful else "_request"


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "field": _field_from_location(tuple(error.get("loc", ()))),
            "message": str(error.get("msg", "Invalid value")),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"errors": errors})


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/devices", status_code=201)
def create_device(payload: DeviceCreate) -> dict[str, Any]:
    # A real application would persist the validated payload here.
    return {"device": payload.model_dump()}
