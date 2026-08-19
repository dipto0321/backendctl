# Tasks: e2e-and-hygiene

## Implementation

- [x] Create `.github/workflows/e2e.yml` with matrix over frameworks × databases
- [x] Create `.github/workflows/ci.yml` with mypy step
- [x] Add empty `src/backendctl/py.typed`
- [x] Fix mypy error in `generators/__init__.py:17` (annotate mapping dict)
- [x] Add `--verbose` flag to `new_command`
- [x] Re-raise exceptions when `--verbose` is set
- [x] Delete stale `dist/backendctl-0.1.0.*` artifacts
- [x] Add `test_verbose_flag_shows_traceback` to `tests/test_cli.py`

## Validation

- [x] `uv run pytest -q` passes (91 tests)
- [x] `uv run ruff check src tests` clean
- [x] `uv run mypy src` clean
