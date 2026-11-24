# CI/CD Policy

## Workflows (`.github/workflows/`)

| File | Job | Steps |
|---|---|---|
| `backend.yml` (existing, kept) | `tests` | install requirements, `ruff check .`, `pytest -q --cov` |
| | `tests-postgres` | pytest with `TEST_DATABASE_URL` on a PostgreSQL 16 service |
| | `migrations` | `alembic upgrade head && alembic check && alembic downgrade base && alembic upgrade head` |
| `frontend.yml` (new) | `frontend-lint-and-build` | `npm ci`, `npm run lint`, `npm run build` (Node 22) |
| `docker.yml` (new) | `docker-validate` | `docker compose config --quiet`, `docker build ./backend` |

## Design decisions

- **Triggers:** `pull_request` (every PR) and `push` to `main` (post-merge sanity). Feature-branch pushes are not triggered separately, so there is no duplicate run per commit.
- **Concurrency:** a new push to a PR cancels the older run of the same workflow.
- **Least privilege:** each workflow declares `permissions: contents: read`.
- **Caching:** pip cache (backend) and npm cache (frontend), keyed on requirements / lock file.
- **Secrets:** none used. The test database credentials (`lumi/lumi`) are throw-away values for an ephemeral CI container. Real credentials must go in GitHub Secrets and never be echoed.
- **No deployment:** the project has no deployment pipeline (only local `docker compose`), so none was added. Docker is only validated and built, never pushed.
- **No path filters:** required checks must always report, otherwise merges block.
- **Dependabot** (`.github/dependabot.yml`) opens monthly PRs for GitHub Actions, npm and pip updates, so they go through the same review and CI.

## Failure behaviour

A failing job turns the PR check red. It blocks merging **only if** the check is listed as required in GitHub (see [branch-protection-policy.md](branch-protection-policy.md)); that is a GitHub setting, not a repo file.

## Known gaps

No frontend unit tests, edge-agent code, ML tests or deployment pipeline exist yet. Actions use major-version tags (`@v4`, `@v5`); pinning to commit SHAs is a possible hardening step.
