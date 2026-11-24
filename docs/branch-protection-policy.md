# Branch Protection Policy

Target configuration for `main`. **Status: NOT VERIFIED.** The repository settings could not be read from this environment (no GitHub CLI or credentials), so nothing here may be described as "active" until an admin applies and checks it (section 5).

## 1. Classic branch protection vs. rulesets

| | Classic branch protection | Repository ruleset |
|---|---|---|
| Layering | One rule per branch pattern | Several rulesets stack; strictest wins |
| Testing | Immediate | Has an *Evaluate* (dry-run) mode |
| Bypass | Admin toggle ("include administrators") | Named bypass list (roles/teams) |
| Visibility | Settings only | Rules visible to anyone with read access |
| Availability | Public repos; private repos need a paid plan | Same plan limits |

**Recommendation: use a ruleset** targeting the default branch (finer bypass control, dry-run mode). Classic protection is an acceptable fallback with the same settings. If the repository is private on a free plan, GitHub enforces neither; the team then follows this policy by convention.

## 2. Recommended settings, reasons and trade-offs

| Setting | Value | Why | Trade-off |
|---|---|---|---|
| Require a pull request | On | No unreviewed code on `main` | Every small change needs a PR |
| Required approvals | **1** (2 only for high-risk changes) | Independent review catches defects | 2 always would stall a 4-person team |
| PR author cannot approve own PR | Built into GitHub | Independence | none |
| Require approval of most recent reviewable push | On | The last pusher cannot self-approve late changes | Reviewer re-checks after each push |
| Dismiss stale approvals | On | Approval applies to the code that was reviewed | Re-approval after fixes |
| Require conversation resolution | On | Comments aren't forgotten | Needs discipline |
| Require status checks | On (section 3) | Broken code can't merge | A flaky check blocks everyone |
| Require branch up to date | On | Checks ran on the code that actually lands | Extra updates when several PRs are open |
| Block force pushes | On | History can't be rewritten | none |
| Block deletions | On | `main` can't be removed | none |
| Restrict direct pushes | On (PR only) | Enforces the workflow | Emergencies need bypass |
| Bypass | Empty, or repo owner only (break-glass) | Rules apply to admins too | Owner can still override; log it in the PR |
| Require linear history | **Off** | History uses merge commits; enabling forbids them | History stays non-linear |
| Require signed commits | Off | Not set up by the team | Less authorship proof |

## 3. Required status checks (actual job names)

GitHub matches checks by **job name** as shown in the Actions tab.

| Workflow file | Check name | What it proves |
|---|---|---|
| backend.yml | `tests` | `ruff check` + pytest on SQLite, 95% coverage gate |
| backend.yml | `tests-postgres` | tests against PostgreSQL 16 |
| backend.yml | `migrations` | upgrade head, `alembic check`, downgrade base, upgrade again |
| frontend.yml | `frontend-lint-and-build` | `npm ci`, oxlint, `vite build` |
| docker.yml | `docker-validate` | `docker compose config` + backend image builds |

Not covered because the code doesn't exist yet: edge-agent tests (README only), ML tests (one notebook), frontend unit tests. Add a required check when each appears.

Workflows deliberately have **no path filters**: a skipped required check stays "pending" and blocks merging.

The two new jobs must run once on a PR before GitHub offers them in the required-checks search box.

## 4. Settings in GitHub vs. files in the repo

| Item | Where |
|---|---|
| Workflows, PR template, dependabot config, these docs | Files in repo (active once merged) |
| Branch protection / ruleset, required checks, bypass list | **GitHub settings only** (admin) |
| Jira and GitHub link | Jira / GitHub app settings |

## 5. Admin steps (Settings > Rules > Rulesets > New branch ruleset)

1. Name `protect-main`. Enforcement **Evaluate** first, then **Active** after a trial PR.
2. Target: *Include default branch*.
3. Enable: Restrict deletions; Block force pushes; Require a pull request (approvals = 1, dismiss stale approvals, require approval of the most recent reviewable push, require conversation resolution); Require status checks (add the 5 names above, enable *Require branches to be up to date*).
4. Bypass list: empty, or only the repo owner.
5. Save, then open a test PR and confirm: direct push rejected, merge blocked by a failing check, merge blocked before approval.
6. Fill in the table below.

| Item | Verified by | Date |
|---|---|---|
| Ruleset active | _pending_ | _pending_ |
| Required checks listed | _pending_ | _pending_ |
| Direct push to `main` rejected | _pending_ | _pending_ |
