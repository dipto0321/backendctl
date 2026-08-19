# mongo-full-wiring

## Why

MongoDB was half-wired: FastAPI generated a motor client nobody called, and Flask
used the unmaintained `flask-pymongo` without any sample CRUD usage or tests.
Generated projects had no way to verify MongoDB connectivity.

## What changes

- **FastAPI**: new `modules/items` router with GET/POST on an `items` collection
  via `get_mongo_db()`; `api_v1_router` includes items router when `uses_mongo`;
  `tests/conftest.py` patches mongo with `mongomock-motor`; `tests/test_items.py`
  added; `/health/db` endpoint pings MongoDB.
- **Flask**: replace `flask-pymongo` with plain `pymongo`; new `mongo.py` module
  providing `get_db()` + `close_mongo()` teardown; `extensions.py` drops
  `PyMongo`; `app_init` registers `blueprints/items` when `uses_mongo`;
  `tests/conftest.py` patches `pymongo.MongoClient` with `mongomock`;
  `tests/test_items.py` added; `/health/db` endpoint pings MongoDB.

## Capabilities

- scaffolding (MODIFIED)

## Impact

- FastAPI and Flask projects with MongoDB have working CRUD sample code.
- MongoDB tests run without a live server (mongomock / mongomock-motor).
- Flask no longer depends on the unmaintained `flask-pymongo`.
