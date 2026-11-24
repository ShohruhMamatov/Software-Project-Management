# Change Control Policy

How a change travels from a Jira ticket to `main`. Goal: every change is traceable, reviewed, and tested before it reaches `main`.

> **Configured in GitHub vs. committed in the repo.** Files in this repo (workflows, PR template) are active as soon as they are merged. Branch protection / rulesets are **GitHub settings** and exist only after an administrator applies them (see [branch-protection-policy.md](branch-protection-policy.md)). This document describes the target process; it does not prove the settings are on.

## 1. Branching strategy

Simple trunk-based flow: `main` is always releasable; all work happens on short-lived branches.

| Type | Pattern | Example |
|---|---|---|
| Feature | `feature/SCRUM-123-short-description` | `feature/SCRUM-40-camera-health` |
| Bug fix | `bugfix/SCRUM-123-short-description` | `bugfix/SCRUM-41-login-500` |
| Hotfix | `hotfix/SCRUM-123-short-description` | `hotfix/SCRUM-42-jwt-expiry` |

Existing branches (`SCRUM-26-frontend`, `SCRUM-30-backend-tests-ci`) lack the type prefix. They are already merged and are not renamed; the new pattern applies from now on. (The README's `LUMI-12-...` example is outdated: the Jira project key is `SCRUM`.)

## 2. Commits and Pull Requests

- Commit messages start with the Jira key: `SCRUM-123: Add camera status endpoint`.
- PR title: `SCRUM-123: Description of change`.
- Fill in `.github/pull_request_template.md` (Jira link, reason, risk, components, tests, rollback, reviewer checklist).
- Merge method: the repo history uses merge commits ("Merge pull request #8"). Keep merge commits for now; do **not** enable "require linear history" unless the team switches to squash merging.

## 3. Review procedure

1. Author opens a PR to `main` and requests a review.
2. CI runs automatically (see [ci-cd-policy.md](ci-cd-policy.md)).
3. A teammate (never the author) reviews, comments, and approves.
4. Author fixes comments; reviewer resolves conversations. New commits dismiss old approvals, so the reviewer re-approves.
5. When all required checks are green, approvals are present and conversations are resolved, the PR is merged.

Team size is 4, so the minimum is **1 approval**. Use 2 for high-risk changes (auth, DB schema, camera credentials) by team agreement.

## 4. Emergency hotfix

Used only for a production-breaking bug or security issue.

1. Create a Jira bug and branch `hotfix/SCRUM-123-description` from `main`.
2. Make the smallest possible fix; add a test if feasible.
3. Open a PR marked **HOTFIX**. CI and 1 approval are still required: the fast path is a faster review, not skipping it.
4. If no reviewer is available, a repository admin may bypass **only** the approval, writes the reason in the PR, and a post-merge review is done within 1 working day.
5. After merge, write a short note in the Jira issue (cause, fix, follow-up).

## 5. Rollback

- **Code:** on GitHub open the merged PR and click *Revert*. This creates a new PR that goes through the normal checks. Never force-push `main`.
- **Database:** if the PR contained a migration, run `alembic downgrade -1` (CI tests that migrations downgrade) together with deploying the revert.
- **Docker:** redeploy the previous commit: `git checkout <good-sha>` then `docker compose up --build -d`.
- Record the rollback in the Jira issue.

## 6. Roles

| Role | Responsibility |
|---|---|
| Author | Creates the Jira-linked branch, fills the PR template, keeps CI green, answers comments |
| Reviewer | Independent teammate; checks the reviewer checklist, approves or requests changes |
| QA & DevOps (Shamsiddinxoja Abduraximov) | Owns CI workflows and the required-check list |
| Repository admin (repo owner) | Applies and maintains GitHub branch protection / rulesets; handles emergency bypass |
| PM (Temur Erkinov) | Keeps Jira issues and this policy consistent with the process |
