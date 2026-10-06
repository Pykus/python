# Flask application factory, configuration, and testable extensions

A Flask application often starts as a single `app.py`. That is useful for a prototype, but it becomes awkward when the same application must run with different configuration in development, tests, production, or CLI jobs. The application-factory pattern creates the Flask instance in a function and initializes extensions against that instance.

## When to use it

Use a factory when the project has multiple environments, automated tests, blueprints, database extensions, background integrations, or more than one deployment configuration. A tiny one-file internal tool may not need this structure. The goal is not to add folders; it is to remove global initialization that makes configuration and testing unpredictable.

## Configuration classes

```python
import os

class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    JSON_SORT_KEYS = False

class ProductionConfig(BaseConfig):
    DEBUG = False
    DATABASE_URL = os.environ["DATABASE_URL"]

class TestConfig(BaseConfig):
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"
```

Never keep production secrets in the repository. Environment variables or a dedicated secret store are preferable. Also avoid reading every environment variable at module import time when tests need to override it later.

## Extensions without a global app

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
```

The extension object may be global; the Flask application should not be. Bind the extension inside the factory:

```python
from flask import Flask

def create_app(config_object=BaseConfig):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)

    from .api import api
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/health/live")
    def liveness():
        return {"status": "ok"}

    return app
```

This prevents importing a preconfigured application before a test has a chance to select its configuration.

## Blueprint

```python
from flask import Blueprint, current_app

api = Blueprint("api", __name__)

@api.get("/config-check")
def config_check():
    return {
        "testing": current_app.testing,
        "debug": current_app.debug,
    }
```

Use `current_app` inside request/application context instead of importing an `app` object from another module. Importing the app from a blueprint is a common source of circular imports.

## Running the application

```python
# wsgi.py
from myservice import create_app, ProductionConfig

app = create_app(ProductionConfig)
```

A WSGI server can then load `wsgi:app`. For local development, a small launcher can choose a development configuration explicitly.

## Testing with a real factory

```python
import pytest
from myservice import create_app, TestConfig, db

@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

def test_factory_uses_test_configuration(client):
    response = client.get("/api/config-check")
    assert response.status_code == 200
    assert response.get_json()["testing"] is True
```

The test creates a fresh configured app instead of mutating a production singleton. This makes test order less significant and supports isolated fixtures.

## Typical pitfalls

**Circular imports:** keep extension instances in a neutral module and import blueprints inside `create_app` if necessary.

**Configuration loaded too early:** do not copy values into module-level constants when they should differ between app instances.

**Creating tables on every startup:** schema management belongs in migrations, not in the factory. `create_all()` is reasonable in disposable tests, not as production migration logic.

**Using Flask's development server in production:** the factory pattern does not change the need for a production WSGI server.

**Leaking test configuration:** tests should pass `TestConfig` explicitly and should never depend on whatever environment happened to start the test process.

## Practical scenarios

A school inventory API can use PostgreSQL in production and an isolated database in tests. An administrative service can disable outbound mail in its test configuration. A monitoring adapter can replace a real external endpoint with a fake implementation. A CLI maintenance command can construct the same application and reuse database configuration without starting an HTTP listener.

## Verification

Run the test suite twice with different test ordering. Start the development app and confirm its configuration differs from the test fixture. Start the production WSGI entry point with required environment variables and check `/health/live`. Finally, deliberately remove a required production variable: startup should fail clearly rather than silently falling back to an unsafe value.

A good Flask factory gives each runtime an explicit configuration boundary. Extensions remain reusable, blueprints remain independent, and tests construct exactly the application they intend to exercise.
