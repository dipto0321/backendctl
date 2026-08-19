## ADDED Requirements

### Requirement: SHALL NOT trigger ruff E402 in generated Django settings

The `settings_base()` template MUST have all imports at the top of the file.

#### Scenario: No mid-file imports in Django settings
- **WHEN** the Django settings template is rendered
- **THEN** `config/settings/base.py` compiles without `E402` violations

### Requirement: SHALL return JSON 500 errors from generated FastAPI apps

FastAPI apps MUST have a generic exception handler that returns JSON instead of
HTML tracebacks.

#### Scenario: FastAPI unhandled exception returns JSON
- **WHEN** an unhandled exception occurs in a generated FastAPI app
- **THEN** the response is `{"detail": "Internal server error"}` with status 500

### Requirement: SHALL return JSON 500 errors from generated Flask apps

Flask apps MUST have a generic error handler that returns JSON instead of HTML
tracebacks.

#### Scenario: Flask unhandled exception returns JSON
- **WHEN** an unhandled exception occurs in a generated Flask app
- **THEN** the response is `{"detail": "Internal server error"}` with status 500

### Requirement: SHALL wire custom exception handler in generated Django DRF apps

Django settings MUST wire `core.exceptions.custom_exception_handler` into
`REST_FRAMEWORK`.

#### Scenario: Django DRF exception handler is configured
- **WHEN** the Django settings template is rendered
- **THEN** `REST_FRAMEWORK["EXCEPTION_HANDLER"]` equals `"core.exceptions.custom_exception_handler"`

### Requirement: SHALL configure development logging in generated apps

When `DEBUG=true`, generated apps MUST configure basic logging to stdout.

#### Scenario: FastAPI logs in debug mode
- **WHEN** a generated FastAPI app starts with `DEBUG=true`
- **THEN** `logging.basicConfig(level=logging.INFO)` is called

#### Scenario: Flask logs in debug mode
- **WHEN** a generated Flask app starts with `DEBUG=true`
- **THEN** `logging.basicConfig(level=logging.INFO)` is called

#### Scenario: Django logging dict is present
- **WHEN** the Django settings template is rendered
- **THEN** a `LOGGING` dict with a console handler is defined
