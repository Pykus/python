from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    base_url: str
    version: str | None
    latency_ms: int | None
    models: list[str]
    required_model: str | None
    required_model_present: bool | None
    error: str | None


def fetch_json(url: str, timeout: float) -> tuple[dict, int]:
    started = time.perf_counter()
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "ollama-probe/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    latency_ms = round((time.perf_counter() - started) * 1000)
    if not isinstance(payload, dict):
        raise ValueError("Ollama returned a non-object JSON payload")
    return payload, latency_ms


def probe(
    base_url: str,
    *,
    timeout: float = 3.0,
    required_model: str | None = None,
) -> ProbeResult:
    normalized = base_url.rstrip("/")

    try:
        version_payload, version_latency = fetch_json(
            f"{normalized}/api/version",
            timeout,
        )
        tags_payload, tags_latency = fetch_json(
            f"{normalized}/api/tags",
            timeout,
        )

        version = str(version_payload.get("version", "")).strip() or None
        models = sorted(
            {
                str(model.get("name", "")).strip()
                for model in tags_payload.get("models", [])
                if isinstance(model, dict) and str(model.get("name", "")).strip()
            }
        )

        present: bool | None = None
        if required_model:
            present = required_model in models

        return ProbeResult(
            ok=present is not False,
            base_url=normalized,
            version=version,
            latency_ms=version_latency + tags_latency,
            models=models,
            required_model=required_model,
            required_model_present=present,
            error=None,
        )
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return ProbeResult(
            ok=False,
            base_url=normalized,
            version=None,
            latency_ms=None,
            models=[],
            required_model=required_model,
            required_model_present=None,
            error=f"{type(exc).__name__}: {exc}",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only Ollama API readiness probe"
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
        help="Ollama API base URL",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="Timeout per API request in seconds",
    )
    parser.add_argument(
        "--require-model",
        help="Fail with exit code 3 when this model is not installed",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print machine-readable JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout <= 0:
        print("error: --timeout must be greater than zero", file=sys.stderr)
        return 2

    result = probe(
        args.base_url,
        timeout=args.timeout,
        required_model=args.require_model,
    )

    if args.as_json:
        print(json.dumps(asdict(result), indent=2))
    elif result.error:
        print(f"UNHEALTHY: {result.error}")
    else:
        print(f"Ollama version: {result.version or 'unknown'}")
        print(f"API latency: {result.latency_ms} ms")
        print(f"Models: {', '.join(result.models) if result.models else '(none)'}")
        if result.required_model:
            status = "present" if result.required_model_present else "missing"
            print(f"Required model {result.required_model!r}: {status}")

    if result.error:
        return 2
    if result.required_model_present is False:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
