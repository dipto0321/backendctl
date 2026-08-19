## ADDED Requirements

### Requirement: SHALL remove JWT auth artifacts from generated Flask projects when auth=none

When `auth=none` is selected for Flask, the generator SHALL NOT emit any JWT
auth files or dependencies.

#### Scenario: Flask auth=none skips auth files
- **WHEN** a user runs `backendctl new demo --framework flask --auth none --yes`
- **THEN** no `blueprints/auth/`, `blueprints/users/`, `models/user.py`, or
  `tests/test_auth.py` are created, and `pyproject.toml` does not contain
  `flask-jwt-extended`

#### Scenario: Flask auth=none omits JWT from config
- **WHEN** the Flask config template is rendered with `auth=none`
- **THEN** `config.py` does not contain `JWT_SECRET_KEY` or JWT expiry fields,
  and `.env.example` does not contain JWT settings

### Requirement: SHALL remove JWT auth artifacts from generated Django projects when auth=none

When `auth=none` is selected for Django, the generator SHALL NOT emit JWT auth
files or dependencies, but MUST keep the custom User model.

#### Scenario: Django auth=none skips auth files
- **WHEN** a user runs `backendctl new demo --framework django --auth none --yes`
- **THEN** no `apps/authentication/` content (except migrations/__init__.py),
  no `apps/users/serializers.py`, `views.py`, or `urls.py` are created,
  and `pyproject.toml` does not contain `djangorestframework-simplejwt`

#### Scenario: Django auth=none sets permissive default permissions
- **WHEN** the Django settings template is rendered with `auth=none`
- **THEN** `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` is set to
  `AllowAny` and `DEFAULT_AUTHENTICATION_CLASSES` is omitted

### Requirement: SHALL include a health test in all generated projects

Every generated project MUST contain a `tests/test_health.py` that asserts
`/health` returns 200, giving `auth=none` suites a non-empty, boot-proving test.

#### Scenario: Health test exists for all frameworks
- **WHEN** generation completes for any framework
- **THEN** `tests/test_health.py` exists and compiles
