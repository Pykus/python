# Flask request correlation ID

Attach one request ID to logs and responses so a request can be traced across services.

```python
from uuid import uuid4
from flask import g, request

g.request_id = request.headers.get("X-Request-ID") or str(uuid4())
```

Return the same ID in the response and include it in application logs. Do not use it as authentication data.
