# generated-runtime-quality

## Why

Generated Django projects had a mid-file `from datetime import timedelta` import
triggering ruff `E402`. None of the frameworks shipped JSON error handlers or
logging configuration, meaning generated apps returned HTML tracebacks to API
clients and produced no structured logs in development.

## What changes

- **Django E402**: move `from datetime import timedelta` to the top of
  `settings_base()` (with other imports); delete the mid-file line.
- **FastAPI**: add a JSON `@app.exception_handler(Exception)` returning
  `{"detail": "Internal server error"}` with 500; add `logging.basicConfig`
  gated on `settings.DEBUG`.
- **Flask**: register `@app.errorhandler(Exception)` → JSON in `app_init`;
  configure `logging.basicConfig` in `create_app` when `DEBUG` is true.
- **Django**: wire `REST_FRAMEWORK["EXCEPTION_HANDLER"]` to
  `core.exceptions.custom_exception_handler`; add a `LOGGING` dict to
  `settings_base`.

## Capabilities

- scaffolding (MODIFIED)

## Impact

- Generated Django projects pass ruff lint without E402 violations.
- All generated frameworks return JSON 500 errors instead of HTML tracebacks.
- Development logging is enabled when `DEBUG=true`, improving debuggability.
