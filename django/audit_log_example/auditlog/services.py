from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import AuditEntry

_BLOCKED_KEY_PARTS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
}


def sanitize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}

    clean: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized = str(key).strip().lower()
        if any(part in normalized for part in _BLOCKED_KEY_PARTS):
            continue

        if isinstance(value, Mapping):
            clean[str(key)] = sanitize_metadata(value)
        elif isinstance(value, (str, int, float, bool)) or value is None:
            clean[str(key)] = value
        else:
            clean[str(key)] = str(value)

    return clean


def record_audit_event(
    *,
    actor: str,
    action: str,
    target_type: str,
    target_key: str,
    request_id: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> AuditEntry:
    actor = actor.strip()
    action = action.strip()
    target_type = target_type.strip()
    target_key = target_key.strip()

    if not all((actor, action, target_type, target_key)):
        raise ValueError(
            "actor, action, target_type, and target_key are required"
        )

    return AuditEntry.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_key=target_key,
        request_id=request_id.strip(),
        metadata=sanitize_metadata(metadata),
    )
