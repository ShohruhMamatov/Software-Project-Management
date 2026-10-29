# LUMI Backend: Testing Guide

**For:** Shamsiddin (QA & DevOps) · **From:** Shohruh (backend)

The MVP backend is written (auth, stores, cameras, zones, events, edge-agent endpoints), but it has **no tests yet**. You own the whole test suite:

1. set up the test infrastructure (`conftest.py`, §2),
2. write the tests in §4, in priority order,
3. set up CI so every PR runs them (§5),
4. run the manual end-to-end check (§6).

If a test finds a bug, **don't fix the app code in the same PR**. Open a GitHub issue (or tell me) and mark the test `@pytest.mark.xfail(reason="issue #N")` so CI stays green until it's fixed.

---

## 1. Setup

```powershell
cd backend
python -m venv .venv            # first time only
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q                       # all tests
pytest tests/test_auth.py -v    # one file
pytest -k review -v             # tests whose name contains "review"
```

`pytest.ini` already sets `pythonpath = .` and `testpaths = tests`, so `from app.main import app` works in tests.

To try endpoints by hand, run the server (`uvicorn app.main:app --reload`) and open http://localhost:8000/docs. The full API (bodies, responses, status codes) is described in [frontend-spec.md §8](frontend-spec.md#8-api-reference). Read the code in `backend/app/routers/` for exact behaviour.

---

## 2. Test infrastructure to build

### Use an in-memory SQLite DB, not Postgres
Tests should need no database server, so they run fast on any laptop and in CI. Override the app's `get_db` dependency with a fresh **in-memory SQLite** DB per test, and point `MEDIA_DIR` at pytest's `tmp_path`, so tests never touch `dev.db` or real files. The models only use portable column types, so this works. Postgres is still checked separately in CI (§5).

Start `backend/tests/conftest.py` with this fixture. It's the fiddly part, so here it is:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.config import settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # StaticPool + check_same_thread=False: one shared in-memory DB across TestClient threads.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "media_dir", str(tmp_path / "media"))
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()
```

### Helpers and fixtures to add yourself
Build these on top of `client`, so each test stays short:

| Name | Should give you |
|---|---|
| `register(client, email=..., password=...)` (plain function) | registers a user via `POST /auth/register`, returns `{"Authorization": "Bearer ..."}` |
| `owner` fixture | an owner **with a store**: headers + the store's `api_key` + `store_id` (from `POST /stores`) |
| `camera` fixture | a camera created via `POST /cameras` in the owner's store. Give it a password with special characters, like `p@ss:w/rd#1`, to test URL encoding and leaks. |
| `staff` fixture | a staff user in the owner's store (snippet in §4 P1) |
| `post_event(client, api_key, camera_id, ...)` | sends `POST /agent/events` as multipart form data, optionally with fake files |

For uploads, use fake bytes instead of real media files, e.g. `FAKE_JPEG = b"\xff\xd8\xff\xe0fake"`, sent as `files={"snapshot": ("snap.jpg", FAKE_JPEG, "image/jpeg")}`.

Suggested files: `test_health.py`, `test_auth.py`, `test_stores.py`, `test_cameras.py` (+ zones + RTSP builder), `test_agent.py`, `test_events.py`.

### Style
- **One behaviour per test**, named `test_<what>_<expected>`, e.g. `test_login_wrong_password_is_401`.
- Arrange → act → assert, with a blank line between the parts when the test is longer than a few lines.
- Assert the **status code and the important fields**, not whole JSON blobs, so tests don't break when we add fields.
- No real network, no sleeping, no dependence on test order.

---

## 3. Who can do what (the rules to test)

| Rule | Where |
|---|---|
| Every endpoint except `/health`, `/auth/register`, `/auth/login` needs a valid `Bearer` token → else **401** | `app/security.py` |
| `/agent/*` needs `X-API-Key` of a store → else **401** | `get_agent_store` |
| A user without a store gets **400** "Create a store first" on store/camera/event endpoints | `get_current_store` |
| Only `owner` may change store, cameras, zones, API key → staff gets **403** | `require_owner` |
| `staff` **may** review events | `/events/{id}/review` |
| Another store's camera/event is always **404**, never 403, so ids don't leak | `get_store_camera`, `get_store_event` |
| Camera password is never returned by `/cameras*`; only `/agent/config` returns the real RTSP URL | `routers/cameras.py`, `routers/agent.py` |

---

## 4. Tests to write (in priority order)

Tick them off in your PR description. Several small PRs (P0, then P1, …) are better than one huge one.

### P0: main flows work (start here)
- [ ] `GET /health` → 200 `{"status": "ok"}`.
- [ ] **Register** → 201 with `access_token` and `user`; role is `owner`, `store_id` null; email is stored lower-case.
- [ ] Register with an already used email (any letter case) → 409.
- [ ] **Login** with correct password → 200 + token; wrong password or unknown email → 401; `GET /auth/me` with that token → the user; no token or a garbage token → 401.
- [ ] **Create store** → 201, `api_key` starts with `lumi_`, `/auth/me` now has `store_id`; `GET /stores/me` has `has_api_key: true` and **no** `api_key`; second `POST /stores` → 409.
- [ ] User without a store → 400 on `GET /stores/me` and `GET /cameras`.
- [ ] **Rotate API key** → the old key gets 401 on `/agent/config`, the new one 200.
- [ ] **RTSP builder** (`app.hikvision.build_rtsp_url`): channel 1 sub → `/Streaming/Channels/102`, channel 3 main → `/301`, password `p@ss:w/rd#1` is percent-encoded (`p%40ss%3Aw%2Frd%231`).
- [ ] **Cameras CRUD**: create returns masked URLs (`rtsp://admin:****@...`), list, get, `PATCH` channel → URL updates, delete → 204 then 404.
- [ ] **Zones**: `PUT` two zones → both returned; `PUT` again with one → only one remains (replace, not append).
- [ ] **Agent config** (`X-API-Key`): contains the real RTSP URL with the encoded password, the threshold and the zones; inactive cameras are left out; missing or wrong key → 401.
- [ ] **Heartbeat** with a snapshot → 204; camera becomes `online: true`, `has_snapshot: true`; `GET /cameras/{id}/snapshot` returns the same bytes.
- [ ] **Event flow**: agent posts an event with clip + snapshot → 201 `pending`; `GET /events?status=pending` lists it; clip and snapshot download with the same bytes; `POST /events/{id}/review {"status": "dismissed"}` → status changes, `reviewed_by` set, gone from the pending list.
- [ ] Events are **newest first** (by `started_at`); `after_id` returns only newer events.
- [ ] Agent event with a disallowed file type (`evil.exe`) → 400; unknown `camera_id` → 404.

### P1: security & permissions (most important after P0)
- [ ] **Staff role.** There's no API to create staff yet, so add a `staff` fixture that inserts the user straight into the test DB (snippet below). Then test:
  - staff gets **403** on `POST/PATCH/DELETE /cameras`, `PUT /cameras/{id}/zones`, `PATCH /stores/me`, `POST /stores/me/api-key`
  - staff gets **200** on `GET /cameras`, `GET /events`, and **can review** an event
- [ ] **Expired token** → 401. Use `monkeypatch.setattr(settings, "jwt_expire_minutes", -1)`, register, then call `/auth/me`.
- [ ] Token signed with a **different secret** → 401 (create one with `jwt.encode(..., "other-secret")`).
- [ ] **Inactive user** (`is_active=False` in the DB) → login 401, and an existing token stops working.
- [ ] Camera password never leaks: after creating a camera, `"p@ss"` and `"rd#1"` appear nowhere in the text of `GET /cameras`, `GET /cameras/{id}`, `PATCH` responses.
- [ ] `password_hash` and `api_key_hash` never appear in any response (`/auth/*`, `/stores/me`).
- [ ] **Other store** (register a second owner with their own store): cannot see the first store's cameras (`GET /cameras` is empty, `GET /cameras/{id}` → 404), events (`GET /events` total 0, `GET /events/{id}` → 404), and can't review, `PUT` zones, `PATCH`/`DELETE` cameras or download clips → **404**.
- [ ] Agent of store A posts an event or a heartbeat for store B's camera → **404**.

```python
# conftest.py — staff fixture (no staff API yet, so insert directly)
from app.models import User, UserRole
from app.security import hash_password

@pytest.fixture
def staff(client, owner):
    db = next(app.dependency_overrides[get_db]())
    db.add(User(email="staff@lumi.uz", password_hash=hash_password("secret123"),
                role=UserRole.staff, store_id=owner["store_id"], is_active=True))
    db.commit()
    db.close()
    token = client.post("/auth/login", json={"email": "staff@lumi.uz", "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### P2: input validation (expect **422**)
- [ ] Register: missing fields, password of 73+ chars, `full_name` over 120 chars.
- [ ] Camera: `port` 0 and 65536, `channel` 0 and 65, `threshold` -0.1, empty `name`, missing `rtsp_password` on create.
- [ ] Zones: unknown `type` ("door"), a point with 3 numbers, empty list `[]` (**allowed**: clears zones → 200).
- [ ] Events list: `status=foo`, `limit=0`, `limit=201`, `offset=-1`.
- [ ] Review: `{"status": "pending"}` and `{"status": "maybe"}` → 422.
- [ ] Agent event: missing `camera_id`, `started_at="yesterday"`, `score=-0.1`.

### P3: behaviour
- [ ] Events **pagination**: create 5 events; `limit=2&offset=2` returns the 3rd and 4th newest, `total` is 5.
- [ ] `camera_id` filter returns only that camera's events (make 2 cameras).
- [ ] Re-review: dismiss then confirm → status `confirmed`, `reviewed_at` updated.
- [ ] `GET /events/{id}/clip` on an event without a clip → 404.
- [ ] `PATCH /cameras/{id}` with `{}` changes nothing; with only `rtsp_password` the URL in `/agent/config` changes (exists), other fields don't.
- [ ] **Deleting a camera** removes its events and zones *and their files on disk*: check that the files under `settings.media_dir` are gone.
- [ ] Heartbeat with a new snapshot **deletes the old snapshot file**.
- [ ] Upload too large → **413**. Use `monkeypatch.setattr("app.media.MAX_UPLOAD_BYTES", 10)` instead of sending 50 MB.
- [ ] Upload allowed types: `.mp4` clip and `.png` snapshot work; `.gif` snapshot → 400.
- [ ] Camera is `online: false` when `last_seen_at` is older than `camera_online_seconds` (`monkeypatch` the setting to `0`).
- [ ] Timestamps in responses always end with an offset (`+00:00`).
- [ ] RTSP builder: channel 12 sub → `/Streaming/Channels/1202`; username with `@` is encoded.

### P4: Postgres
The unit tests use SQLite. Postgres can behave differently (timezones, constraints), so CI also needs to:
- [ ] run `alembic upgrade head`, `alembic downgrade base`, `alembic upgrade head` on a real Postgres (§5);
- [ ] *(nice to have)* run the whole pytest suite against Postgres too.

### Open question (ask me before writing the test)
- An event posted for a camera with `is_active=false` is currently **accepted**. The agent skips inactive cameras anyway. Should the backend reject it? Write it down if you think it's wrong.

---

## 5. CI: GitHub Actions

Ticket: *"CI with GitHub Actions: lint and tests for backend and frontend"*. Starting point, `.github/workflows/backend.yml`:

```yaml
name: backend
on:
  pull_request:
  push:
    branches: [main]

jobs:
  tests:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: backend/requirements.txt
      - run: pip install -r requirements.txt
      - run: pytest -q

  migrations:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: lumi
          POSTGRES_PASSWORD: lumi
          POSTGRES_DB: lumi
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U lumi" --health-interval 5s --health-timeout 3s --health-retries 10
    env:
      DATABASE_URL: postgresql+psycopg://lumi:lumi@localhost:5432/lumi
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: alembic upgrade head && alembic downgrade base && alembic upgrade head
```

Then in GitHub → Settings → Branches → `main` protection, make **both jobs required checks**.

Optional: add `ruff` for linting (`pip install ruff` and `ruff check .`). If you add it, put it in `requirements.txt` and fix the warnings in a separate PR.

---

## 6. Manual end-to-end check (before the demo)

With the backend running (`docker compose up --build`, or uvicorn with SQLite):

1. In `/docs`: register → Authorize → `POST /stores` (save the `api_key`) → `POST /cameras`.
2. `python scripts/send_test_event.py --api-key <key> --camera-id 1 --heartbeat-only --snapshot frame.jpg` → `GET /cameras` shows `online: true`, `has_snapshot: true`.
3. `python scripts/send_test_event.py --api-key <key> --camera-id 1 --snapshot frame.jpg --clip clip.webm` → `GET /events?status=pending` lists it; `/events/1/clip` downloads the video.
4. `POST /events/1/review {"status":"confirmed"}` → it's gone from the pending list.
5. Restart the containers → data is still there (Postgres volume).
6. Once the frontend exists, repeat steps 2–4 through the UI, using the checklist in [frontend-spec.md §10](frontend-spec.md#10-definition-of-done-for-the-midterm-demo).

Write down results (pass/fail, screenshots for failures) in the test plan doc. That's your *"Test plan and end-to-end test"* ticket.

---

## 7. Rules

- Branch name with the Jira key, e.g. `LUMI-23-backend-tests`. Open a PR; main needs 1 review.
- Never commit `.env`, real camera passwords, or video files. `.gitignore` already blocks `*.mp4`/`*.webm`, so tests use fake bytes for uploads (see §2).
- Tests must pass on Windows and in CI (Linux): use `tmp_path`, never hard-coded paths.

Questions → Shohruh.
