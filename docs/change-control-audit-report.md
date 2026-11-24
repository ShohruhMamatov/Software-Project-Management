# Change Control Audit Report: LUMI

Scope: repository `ShohruhMamatov/Software-Project-Management`, local clone at commit `b79351f`. Date: 2026-11-24.

## 1. Method and limits

Audited the files in the repository. **GitHub settings (branch protection, rulesets, merge options) could not be read**: no GitHub CLI or credentials were available. Statements about PR #8 (approval, resolved comments, 3 passing checks) come from the assignment brief and were not re-verified.

## 2. Findings

| Area | Finding | Evidence |
|---|---|---|
| CI backend | Strong: lint, tests with 95% coverage gate, PostgreSQL tests, migration up/down check | `backend.yml` jobs `tests`, `tests-postgres`, `migrations` |
| CI frontend | **Missing**: no lint or build check | no frontend workflow before this change |
| CI Docker | **Missing**: compose file and image build unchecked | none |
| CI edge-agent / ML | Nothing to test yet (README only, one notebook) | `edge-agent/`, `ml/` |
| Workflow permissions | No `permissions:` block (default token rights) | `backend.yml` before change |
| Duplicate runs | Triggers are `pull_request` + `push: main`: no duplicates, but no cancel of superseded runs | `backend.yml` |
| Branch names | Pattern `SCRUM-26-frontend`; README says `LUMI-12-...` (wrong key); no type prefix | `git branch -a`, README |
| Commit / PR titles | `SCRUM-26: ...` style is already used: good traceability | `git log` |
| PR template | Missing | `.github/` had only issue templates |
| Merge method | Merge commits | `git log` ("Merge pull request #8") |
| Dependency updates | No automation | none |
| Branch protection | **Unknown** | not readable |

Strengths: strict backend CI, consistent Jira keys in commits, documented test plan. Weaknesses: half the product (frontend) unchecked, no PR template, no written change policy. Main risk: if branch protection is off or the checks aren't marked required, the rest is only convention.

## 3. Changes made (branch `feature/change-control-policy`)

| File | Type | Change | Why |
|---|---|---|---|
| `.github/workflows/backend.yml` | modified | added `permissions: contents: read` and `concurrency` only; jobs untouched | least privilege, save CI minutes |
| `.github/workflows/frontend.yml` | new | `npm ci`, lint, build on Node 22 with npm cache | closes the frontend gap |
| `.github/workflows/docker.yml` | new | `docker compose config`, backend image build | catches broken compose/Dockerfile |
| `.github/dependabot.yml` | new | monthly updates for actions, npm, pip | keeps dependencies supported |
| `.github/pull_request_template.md` | new | Jira, reason, risk, components, tests, rollback, checklists | consistent, reviewable PRs |
| `docs/change-control-policy.md` | new | branching, review, hotfix, rollback, roles | process definition |
| `docs/branch-protection-policy.md` | new | settings with trade-offs, required check names, admin steps | what the admin must configure |
| `docs/ci-cd-policy.md` | new | workflow design decisions | explain CI |
| `docs/change-control-audit-report.md` | new | this report | assignment deliverable |
| `README.md` | modified | branch example `LUMI-12-...` changed to the `feature/SCRUM-...` convention | removes a contradiction |

Before / after: 1 workflow with 3 jobs and no explicit permissions, no PR template, no policy docs → 3 workflows with 5 required-check candidates, least-privilege permissions, PR template, 4 policy docs.

## 4. Validation results (run locally)

| Check | Result |
|---|---|
| `ruff check .` (backend) | passed |
| `pytest -q --cov` (backend, SQLite) | 343 passed, 5 skipped, 15 xfailed, coverage 100% |
| `npm run lint` | passed |
| `npm run build` | passed |
| `docker compose config --quiet` | passed |
| `docker build ./backend` | passed |
| YAML parse of all files in `.github/` | passed |

Not run locally: the 5 PostgreSQL tests (skipped without `TEST_DATABASE_URL`) and `alembic downgrade/upgrade` (the CI `migrations` job does this; the API container already applies `upgrade head` successfully). The new workflows have **not** run on GitHub yet.

## 5. Remaining limitations

- GitHub branch protection is **not verified or activated**; see `branch-protection-policy.md` section 5.
- Required-check names for the new jobs only become selectable after one PR run.
- No frontend unit tests, edge-agent, ML tests or deployment pipeline.
- Jira key for this task is unknown; the branch has no `SCRUM-nnn` yet. Rename before opening the PR.
- Actions pinned by major tag, not SHA.
- Jira/GitHub integration settings were not inspected.

## 6. Manual steps for a repository admin

1. Merge this PR (needs review).
2. Settings > Rules > Rulesets: create `protect-main` as described in `branch-protection-policy.md`; use *Evaluate*, then *Active*.
3. Add the 5 required checks: `tests`, `tests-postgres`, `migrations`, `frontend-lint-and-build`, `docker-validate`.
4. Test with a throw-away PR; record the result in the verification table.
5. Optionally enable "Automatically delete head branches" in Settings > General.

## 7. How to defend the decisions

- *One approval, not two:* a 4-person team; two would stall work. High-risk changes get two by agreement.
- *Linear history off:* the existing history uses merge commits; forcing it would break the current workflow.
- *No path filters:* a skipped required check blocks merging.
- *No deployment job:* no deployment architecture exists; inventing one would be guesswork.
- *Ruleset over classic rule:* named bypass list and dry-run mode.
