# FastAPI + Vue: filtering a list with a query parameter

This increment adds a small API contract that is easy to consume from Vue.

```python
from fastapi import FastAPI

app = FastAPI()
ITEMS = ["router", "switch", "monitor", "keyboard"]

@app.get("/items")
def items(q: str = ""):
    needle = q.casefold().strip()
    return [item for item in ITEMS if needle in item.casefold()]
```

Vue can call `/items?q=mon` whenever the search field changes. Keep filtering in the backend when the real dataset is server-side; debounce rapid frontend requests when needed.

**Exercise:** add an optional `limit` parameter and validate that it stays between 1 and 100.