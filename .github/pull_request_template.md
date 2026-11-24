## Jira issue
<!-- PR title must be: SCRUM-123: Short description -->
Closes / relates to: SCRUM-

## What changed
<!-- Short description of the change. -->

## Why
<!-- Reason for the change (requirement, bug, improvement). -->

## Components affected
- [ ] backend
- [ ] frontend
- [ ] database / migrations
- [ ] edge-agent
- [ ] ml
- [ ] docker / CI / docs

## Risk assessment
- [ ] Low (docs, small isolated change)
- [ ] Medium (new feature, touches shared code)
- [ ] High (auth, database schema, camera credentials, CI)

Risk notes:

## Testing performed
<!-- Commands run and results, manual checks, screenshots for UI changes. -->
- [ ] Backend: `ruff check .` and `pytest` pass
- [ ] Frontend: `npm run lint` and `npm run build` pass
- [ ] Migrations tested (up and down), if the schema changed

## Rollback plan
<!-- e.g. "Revert this PR" or "Revert + run `alembic downgrade -1`". -->

## Author checklist
- [ ] Branch name follows `feature|bugfix|hotfix/SCRUM-123-description`
- [ ] No secrets, passwords or camera credentials in the diff
- [ ] Docs updated if behaviour changed

## Reviewer checklist
- [ ] Linked Jira issue matches the change
- [ ] Code is understandable and in scope
- [ ] All CI checks are green
- [ ] Tests cover the change
- [ ] No security or privacy concerns (no face recognition, no leaked data)
- [ ] All review conversations are resolved
