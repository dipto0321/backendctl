## ADDED Requirements

### Requirement: SHALL include a working items CRUD module in FastAPI projects with MongoDB

When `uses_mongo` is true for FastAPI, the generator MUST emit a functional
items module and wire it into the API router.

#### Scenario: FastAPI MongoDB items module exists
- **WHEN** a user runs `backendctl new demo --framework fastapi --db mongodb --yes`
- **THEN** `src/<slug>/modules/items/__init__.py`, `router.py`, and
  `tests/test_items.py` exist and compile

#### Scenario: FastAPI MongoDB health check endpoint exists
- **WHEN** the FastAPI main template is rendered with `uses_mongo=true`
- **THEN** a `/health/db` route is registered that pings MongoDB

### Requirement: SHALL use plain pymongo instead of flask-pymongo in Flask projects with MongoDB

When `uses_mongo` is true for Flask, the generator MUST use `pymongo` directly
with a `get_db()` helper and teardown.

#### Scenario: Flask MongoDB uses pymongo
- **WHEN** a user runs `backendctl new demo --framework flask --db mongodb --yes`
- **THEN** `pyproject.toml` contains `pymongo` but not `flask-pymongo`,
  `src/<slug>/mongo.py` exists with `get_db()` and `close_mongo()`,
  and `src/<slug>/blueprints/items/routes.py` provides GET/POST

#### Scenario: Flask MongoDB health check endpoint exists
- **WHEN** the Flask app template is rendered with `uses_mongo=true`
- **THEN** a `/health/db` route is registered that pings MongoDB via `mongo.db.command("ping")`

### Requirement: SHALL run MongoDB tests without a live server

Generated test suites MUST use `mongomock` (Flask) or `mongomock-motor` (FastAPI)
so CI does not need a running MongoDB instance.

#### Scenario: FastAPI MongoDB tests patch the client
- **WHEN** `tests/conftest.py` is rendered for FastAPI with `uses_mongo=true`
- **THEN** it monkeypatches `core.mongo._client` with `AsyncMongoMockClient`

#### Scenario: Flask MongoDB tests patch the client
- **WHEN** `tests/conftest.py` is rendered for Flask with `uses_mongo=true`
- **THEN** it monkeypatches `pymongo.MongoClient` with `mongomock.MongoClient()`
