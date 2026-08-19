# Tasks: generated-runtime-quality

## Implementation

- [x] Django E402: move `from datetime import timedelta` to top of `settings_base`
- [x] FastAPI: add JSON `@app.exception_handler(Exception)` in `main.py`
- [x] FastAPI: add `logging.basicConfig` gated on `settings.DEBUG`
- [x] Flask: register `@app.errorhandler(Exception)` → JSON in `app_init`
- [x] Flask: configure `logging.basicConfig` in `create_app` when `DEBUG`
- [x] Django: wire `REST_FRAMEWORK["EXCEPTION_HANDLER"]` to `core.exceptions.custom_exception_handler`
- [x] Django: add `LOGGING` dict to `settings_base`

## Validation

- [x] `uv run pytest -q` passes (91 tests)
- [x] `uv run ruff check src tests` clean (no E402)
- [x] `uv run mypy src` clean
