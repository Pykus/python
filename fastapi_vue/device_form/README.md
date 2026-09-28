# FastAPI + Vue validation example

This example shows a complete request-validation flow between a FastAPI backend and a Vue form.

## Why it exists

A raw FastAPI 422 response is useful for machines but awkward for a form. This example normalizes validation errors on the backend and maps them to individual Vue fields without exposing Python exception text to the browser.

The pattern is useful for internal admin panels, CRUD forms, and small APIs where the frontend needs predictable field-level errors.

## Backend

`backend.py` exposes:

- `GET /health`
- `POST /api/devices`

The request model validates a device name, room label, enabled flag, and optional note. A custom `RequestValidationError` handler converts FastAPI/Pydantic errors into:

```json
{
  "errors": [
    {"field": "name", "message": "String should have at least 2 characters"}
  ]
}
```

Run it with:

```bash
python -m pip install -r requirements.txt
uvicorn backend:app --reload
```

## Frontend

`DeviceForm.vue` posts JSON to the API, clears previous validation state, maps `errors[].field` to the matching input, and keeps a separate global error for transport/server failures.

Copy the component into a Vue 3 application and set `API_BASE` if the API is served from a different origin.

## Test

```bash
pytest -q
```

The tests cover a valid request and multiple invalid fields. All sample names are synthetic.
