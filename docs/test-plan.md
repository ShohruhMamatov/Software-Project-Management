# LUMI: Test Plan

Jira: SCRUM-31. Automated backend tests: [PR #7](https://github.com/ShohruhMamatov/Software-Project-Management/pull/7). How to write and run them: [testing-guide.md](testing-guide.md).

## 1. Scope

| Area | How it is tested | State on 2026-10-30 |
|---|---|---|
| Backend API: auth, stores, cameras, zones, events, edge-agent endpoints | Automated (`pytest`) and manual | Tested |
| Database migrations | Automated on Postgres 16 in CI | Tested |
| Review flow through the API | Automated and manual | Tested |
| Review flow through the UI | Manual | Blocked: no frontend yet |
| Detection accuracy | Evaluation notebook, recorded clips | Blocked: SCRUM-38 |
| Alert latency | Manual with recorded clips | Blocked: `app/notify.py` only logs, SCRUM-51 and SCRUM-52 |
| Edge agent | End-to-end with recorded clips | Blocked: SCRUM-48. `scripts/send_test_event.py` stands in for it |

## 2. Test levels

| Level | Tools | When |
|---|---|---|
| Lint | `ruff check .` | Every PR |
| API and unit tests on SQLite | `pytest --cov` | Every PR |
| API and unit tests on Postgres 16 | `pytest` with `TEST_DATABASE_URL` | Every PR |
| Migrations | `alembic upgrade`, `check`, `downgrade`, `upgrade` | Every PR |
| Manual end-to-end | §6 of the testing guide | Before each demo |
| Detection evaluation | Notebook from SCRUM-38 | After each model change |

## 3. Entry and exit criteria

**A PR can be merged when:** all CI jobs are green, it has 1 review, and coverage of `app/` is at least 95%.

**A demo build is ready when:** every case in §4 that is not blocked passes, and no High defect is open on the demo flow.

## 4. Test cases

Status: **Pass**, **Fail**, **Blocked** (cannot run yet). Automated cases point to the test file in `backend/tests/`.

### Login

| ID | Case | Expected | Covered by | Status |
|---|---|---|---|---|
| TC-L1 | Register with a new email | 201, token, role `owner`, no store | `test_auth.py` | Pass |
| TC-L2 | Register with a used email in any letter case | 409 | `test_auth.py` | Pass |
| TC-L3 | Log in with the correct password | 200 and a token | `test_auth.py` | Pass |
| TC-L4 | Log in with a wrong password or unknown email | 401, same message for both | `test_auth.py` | Pass |
| TC-L5 | Token is missing, garbage, expired, or signed with another secret | 401 | `test_auth.py` | Pass |
| TC-L6 | Inactive user logs in or uses an old token | 401 | `test_auth.py` | Pass |
| TC-L7 | Every protected endpoint without credentials | 401 | `test_permissions.py` | Pass |
| TC-L8 | Password over 72 bytes | 422 | `test_auth.py` | Fail: SCRUM-63 |
| TC-L9 | `NaN` in the login body | 422 | `test_validation.py` | Fail: SCRUM-57 |
| TC-L10 | Log in through the UI | Dashboard opens | Manual | Blocked: SCRUM-26 |

### Review flow

| ID | Case | Expected | Covered by | Status |
|---|---|---|---|---|
| TC-R1 | Agent posts an event with a clip and a snapshot | 201, status `pending` | `test_agent.py` | Pass |
| TC-R2 | Pending list shows the event, files download with the same bytes | 200 | `test_events.py`, manual | Pass |
| TC-R3 | Owner confirms or dismisses | Status changes, `reviewed_by` set, event leaves the pending list | `test_events.py`, manual | Pass |
| TC-R4 | Staff reviews an event | 200 | `test_permissions.py` | Pass |
| TC-R5 | Review is changed later | New status, `reviewed_at` updated | `test_events.py` | Pass |
| TC-R6 | Review with `pending` or an unknown status | 422 | `test_validation.py` | Pass |
| TC-R7 | Another store reviews the event | 404 | `test_permissions.py` | Pass |
| TC-R8 | Review through the UI | Clip plays, status updates | Manual | Blocked: SCRUM-28 |

### Timestamp correctness

| ID | Case | Expected | Covered by | Status |
|---|---|---|---|---|
| TC-T1 | Timestamps in responses are UTC | Offset is zero | `test_events.py` | Pass |
| TC-T2 | Timestamps end with `+00:00` | As in the contract | `test_events.py` | Fail: SCRUM-64 |
| TC-T3 | `started_at` sent with `+05:00` | Same moment returned in UTC | `test_events.py` (Postgres) | Pass |
| TC-T4 | Events are sorted by `started_at`, newest first | Correct order | `test_events.py` | Pass |
| TC-T5 | Event time matches the moment in a recorded clip | Within the target in §5 | Manual | Blocked: SCRUM-22, SCRUM-48 |

### Detection accuracy

| ID | Case | Expected | Covered by | Status |
|---|---|---|---|---|
| TC-D1 | Precision, recall, F1, ROC-AUC on the test split | Within the targets in §5 | SCRUM-38 | Blocked |
| TC-D2 | Staged clips from a real store | Suspicious clips flagged, normal clips not | SCRUM-39, SCRUM-32 | Blocked |
| TC-D3 | Camera threshold changes sensitivity | Lower threshold gives more alerts | SCRUM-55, SCRUM-32 | Blocked |
| TC-D4 | Person exits without passing the checkout zone | Alert is raised | SCRUM-45, SCRUM-32 | Blocked |

### Alert latency

| ID | Case | Expected | Covered by | Status |
|---|---|---|---|---|
| TC-A1 | Time from the moment in the clip to a pending event | Within the target in §5 | SCRUM-32 | Blocked |
| TC-A2 | Time from a pending event to a Telegram message | Within the target in §5 | SCRUM-51, SCRUM-32 | Blocked |
| TC-A3 | Time from a pending event to an email | Within the target in §5 | SCRUM-52, SCRUM-32 | Blocked |
| TC-A4 | Slow alert service does not block the agent upload | Upload still returns quickly | SCRUM-51 | Blocked |

### Security and data isolation

| ID | Case | Expected | Covered by | Status |
|---|---|---|---|---|
| TC-S1 | Staff calls owner-only endpoints | 403 | `test_permissions.py` | Pass |
| TC-S2 | Another store's cameras, events and files | 404 | `test_permissions.py` | Pass |
| TC-S3 | Camera password in dashboard responses | Never appears | `test_permissions.py` | Pass |
| TC-S4 | Password and API key hashes in responses | Never appear | `test_permissions.py` | Pass |
| TC-S5 | Agent uses a rotated API key | 401 | `test_stores.py` | Pass |
| TC-S6 | Agent of one store reports for another store's camera | 404 | `test_agent.py` | Pass |

### Robustness

| ID | Case | Expected | Covered by | Status |
|---|---|---|---|---|
| TC-B1 | Numbers too large for the database | 404 or 422 | `test_validation.py` | Fail: SCRUM-58 |
| TC-B2 | NUL characters in text fields on Postgres | 422 | `test_validation.py` | Fail: SCRUM-59 |
| TC-B3 | `PATCH /stores/me` with a null name | 422 | `test_stores.py` | Fail: SCRUM-60 |
| TC-B4 | Long non-ASCII camera password on Postgres | Stored or 422 | `test_cameras.py` | Fail: SCRUM-61 |
| TC-B5 | Failed upload leaves no files on disk | No files | `test_agent.py` | Fail: SCRUM-62 |
| TC-B6 | Upload of a wrong type or over the size limit | 400 or 413 | `test_agent.py` | Pass |
| TC-B7 | Deleting a camera removes its events, zones and files | All gone | `test_cameras.py` | Pass |

## 5. Proposed targets

The project has no agreed numbers yet, so these are proposals to confirm in the SRS (SCRUM-13).

| Metric | Proposed target |
|---|---|
| Recall on the test split | at least 0.80 |
| Precision on the test split | at least 0.70 |
| Event time compared with the clip | within 2 s |
| Clip moment to pending event | under 30 s |
| Pending event to Telegram or email | under 10 s |

## 6. Manual end-to-end results

Date: 2026-10-30. Code: `main` at `d6ea4c7`. Run with `uvicorn` and a local Postgres 16, because Docker was not available.

| Step | Result |
|---|---|
| 1. Register, create a store and a camera | Pass |
| 2. Heartbeat with a snapshot: camera shows `online: true`, `has_snapshot: true` | Pass |
| 3. Event with a clip and a snapshot: listed as pending, clip downloads with the same bytes | Pass |
| 4. Confirm the event: it leaves the pending list | Pass |
| 5. Restart the API and Postgres: data and clip are still there | Pass, without Docker |
| 5a. The same restart with `docker compose` and its volumes | Not run |
| 6. Steps 2 to 4 through the UI | Blocked: no frontend yet |

## 7. Defects

| Jira | Summary | Priority |
|---|---|---|
| SCRUM-57 | `NaN` or `Infinity` in a JSON body returns 500 | High |
| SCRUM-58 | Integers outside the DB range return 500 | High |
| SCRUM-59 | NUL characters return 500 on Postgres | High |
| SCRUM-60 | `PATCH /stores/me` with a null name returns 500 | Medium |
| SCRUM-61 | Long non-ASCII camera password returns 500 on Postgres | Medium |
| SCRUM-62 | Orphan clip when the snapshot is rejected | Medium |
| SCRUM-63 | Passwords over 72 bytes are truncated | Low |
| SCRUM-64 | Timestamps end with `Z`, not `+00:00` | Low |

## 8. Risks

| Risk | What to do |
|---|---|
| SQLite hides Postgres behaviour (SCRUM-59 and SCRUM-61 did not show on SQLite) | Run the whole suite on Postgres in CI |
| Detection cannot be tested until the model and the agent exist | Keep the blocked cases in this plan, run them in SCRUM-32 |
| Few real clips for evaluation | Use staged clips from SCRUM-39 |
