# FastAPI + Vue: practical health endpoints

A single `{"status": "ok"}` response is usually too weak to be useful. A better pattern is to separate **liveness** from **readiness**:

- **liveness** answers: “is the application process running?”
- **readiness** answers: “is the application ready to serve real traffic?”

## FastAPI

```python
from datetime import UTC, datetime
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="Example API")


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    time_utc: datetime


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: dict[str, bool]


@app.get("/health/live", response_model=HealthResponse)
def health_live() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="example-api",
        time_utc=datetime.now(UTC),
    )


def database_is_available() -> bool:
    # Replace this with a lightweight real check.
    # Do not run expensive queries in a health endpoint.
    return True


@app.get("/health/ready", response_model=ReadinessResponse)
def health_ready() -> ReadinessResponse:
    database_ok = database_is_available()

    return ReadinessResponse(
        status="ready" if database_ok else "not_ready",
        dependencies={
            "database": database_ok,
        },
    )
```

The distinction is useful in production:

- `/health/live` should stay fast and dependency-light,
- `/health/ready` may check critical dependencies,
- monitoring can alert on either endpoint for different reasons,
- a reverse proxy or container platform can stop sending traffic when readiness fails without killing the process.

## Vue: fail fast instead of hanging indefinitely

A frontend status indicator should use a timeout so a dead backend does not leave the UI waiting for the browser's default network timeout.

```javascript
export async function fetchBackendStatus() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3000);

  try {
    const response = await fetch("/health/ready", {
      signal: controller.signal,
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`Health check failed: HTTP ${response.status}`);
    }

    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
}
```

A simple Vue component can then present the result:

```vue
<script setup>
import { onMounted, ref } from "vue";
import { fetchBackendStatus } from "./api/health";

const backendStatus = ref("checking");

onMounted(async () => {
  try {
    const result = await fetchBackendStatus();
    backendStatus.value =
      result.status === "ready" ? "online" : "degraded";
  } catch {
    backendStatus.value = "offline";
  }
});
</script>

<template>
  <span>Backend: {{ backendStatus }}</span>
</template>
```

## Monitoring use

The same endpoints can be checked independently of the frontend:

```bash
curl --fail --silent http://127.0.0.1:8000/health/live
curl --fail --silent http://127.0.0.1:8000/health/ready
```

This makes the endpoint useful beyond the UI: Zabbix, a load balancer, a container runtime or a deployment smoke test can all consume the same contract.

## Keep health checks safe

Avoid putting these inside a health endpoint:

- expensive database queries,
- secrets or credentials,
- stack traces,
- internal hostnames or addresses,
- full dependency diagnostics intended only for administrators.

Expose only the minimum information needed to decide whether the service is alive and ready.
