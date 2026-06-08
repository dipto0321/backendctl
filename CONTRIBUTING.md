# Contributing to backendctl

Thanks for your interest in improving **backendctl**! This document explains how
to propose changes. By participating you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- **Report a bug** — open a [Bug report](../../issues/new?template=bug_report.yml).
- **Request a feature** — open a [Feature request](../../issues/new?template=feature_request.yml).
- **Submit a fix or feature** — open a pull request (see below).
- **Report a security issue** — **do not** open a public issue; follow
  [SECURITY.md](SECURITY.md).

Please search existing issues before opening a new one.

## Development setup

Requires **Python 3.11+** and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/dipto0321/backendctl
cd backendctl
uv sync                       # install runtime + dev dependencies
uv run pre-commit install     # auto-run lint/format checks on each commit
uv run backendctl --help
```

`pre-commit` then runs ruff and basic hygiene checks before every commit. Run it
against the whole repo any time with `uv run pre-commit run --all-files`.

## Workflow (GitHub Flow)

The `main` branch is protected — **nobody pushes directly to it**, including
maintainers. All changes land through pull requests.

1. **Fork** the repository (external contributors) or create a branch
   (maintainers with write access).
2. Create a topic branch from `main`:
   ```bash
   git switch -c feat/short-description    # or fix/…, docs/…, chore/…
   ```
3. Make your change, with tests.
4. Run the full local check (must pass before you open a PR):
   ```bash
   uv run ruff format src tests      # auto-format
   uv run ruff check src tests       # lint
   uv run pytest -q                  # tests
   ```
5. Commit using [Conventional Commits](https://www.conventionalcommits.org/)
   (see below), push your branch, and open a PR against `main`.
6. CI must be green and at least one maintainer must approve before merge.
   We use **squash merge**, so your PR title becomes the commit message —
   make it a valid Conventional Commit.

## Commit message convention

Format: `type(scope): summary`

| Type | When to use |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `chore` | Tooling, deps, build |
| `ci` | CI/CD configuration |
| `perf` | Performance improvement |

Keep the subject short, imperative, and lowercase. Example:
`feat(templates): add litestar framework option`.

## Changing generated templates

The generated project code lives in `src/backendctl/templates/` as functions
that return file contents. When you change a template:

- The generator-matrix tests in `tests/test_generators.py` compile **every**
  generated `.py` file across the framework/option matrix — keep them green.
- If you add a new file to a generator, add it to the relevant `_scaffold()` in
  `src/backendctl/generators/` and, where useful, assert its presence in tests.
- Prefer adding a new option combination to the test matrix when you add a
  feature flag.

## Pull request expectations

- One logical change per PR; keep them focused and reviewable.
- Include tests for new behaviour and bug fixes.
- Update `README.md` / docs when behaviour or usage changes.
- Describe **what** and **why** in the PR body; link the issue it closes.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
