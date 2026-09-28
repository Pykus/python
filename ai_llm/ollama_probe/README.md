# Ollama service probe

This is a small operational probe for checking whether a local or remote Ollama API is reachable and ready for a job that depends on a specific model.

## What it checks

The probe calls two read-only Ollama endpoints:

- `/api/version` to confirm that the service responds;
- `/api/tags` to list locally available models.

It reports request latency, the Ollama version, the discovered model names, and—when requested—whether a required model is present.

## Why this is useful

A simple TCP port check only proves that something is listening. This probe verifies the API shape that an automation, local AI worker, or watchdog actually needs.

Typical uses:

- a scheduled health check before starting an inference job;
- a local watchdog that should distinguish "service unavailable" from "model missing";
- a CI or lab smoke test after an Ollama upgrade;
- a preflight check before a script submits work to a local model server.

## Usage

```bash
python ollama_probe.py
python ollama_probe.py --base-url http://127.0.0.1:11434 --require-model example-model
python ollama_probe.py --json
```

The base URL is configurable so the tool is not tied to a specific environment.

## Exit codes

- `0` — API reachable and required model (if any) is present;
- `2` — API unreachable, timed out, or returned invalid data;
- `3` — API is healthy but the required model is not installed.

No inference request is sent and no server configuration is changed.
