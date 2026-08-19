# Tasks: mongo-full-wiring

## Implementation

- [x] FastAPI: add `modules/items/__init__.py` + `router.py` (GET/POST via `get_mongo_db()`)
- [x] FastAPI: `api_v1_router` includes items router when `c.uses_mongo`
- [x] FastAPI: add `mongomock-motor` to dev deps; patch `core.mongo._client` in tests
- [x] FastAPI: add `tests/test_items.py` when `c.uses_mongo`
- [x] FastAPI: add `/health/db` endpoint when `c.uses_mongo`
- [x] Flask: replace `flask-pymongo` with `pymongo` in `pyproject.toml`
- [x] Flask: new `mongo.py` (`get_db()` + `close_mongo()` teardown)
- [x] Flask: `extensions.py` drops `PyMongo`; `app_init` registers items blueprint
- [x] Flask: add `mongomock` to dev deps; patch `pymongo.MongoClient` in tests
- [x] Flask: add `tests/test_items.py` when `c.uses_mongo`
- [x] Flask: add `/health/db` endpoint when `c.uses_mongo`

## Validation

- [x] `uv run pytest -q` passes (91 tests)
- [x] `uv run ruff check src tests` clean
- [x] `uv run mypy src` clean
