# LUMI – Retail Theft Detection

CS363 Software Project Management, Fall 2026, Team LUMI.

LUMI connects to a store's existing Hikvision cameras (RTSP), flags likely
"left without paying" behaviour with an ML pipeline, and sends an alert
(dashboard + Telegram/email) with a short clip and snapshot.
**A human always reviews the alert.** The system never accuses anyone or acts by itself.

## Repo layout

```
ml/          notebooks + inference code (shared with the edge agent)
backend/     FastAPI + PostgreSQL API
frontend/    React + Vite dashboard
edge-agent/  store-side RTSP reader that runs inference and posts events
docs/        SRS, architecture, DB schema, backlog
scripts/     helper scripts (e.g. creating GitHub issues from the backlog)
```

See [docs/architecture.md](docs/architecture.md) and [docs/db-schema.md](docs/db-schema.md).

## Quick start (backend)

From the repo root (docker-compose.yml lives here so it can read the root `.env`):

```bash
cp .env.example .env          # then fill in real values
docker compose up --build     # Postgres + API (runs migrations) on http://localhost:8000
# Health check: http://localhost:8000/health
# API docs:     http://localhost:8000/docs
```

Run the tests locally:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
pytest
```

## Team

| Person | Role |
|---|---|
| Temur Erkinov | PM & requirements, alerts, docs |
| Shohruh Mamatov | Backend, architecture, ML lead |
| Abdurahmon Abdurazzoqov | Frontend & UI/UX, zone rule |
| Shamsiddinxoja Abduraximov | QA & DevOps, edge agent, CI |

## Working rules

- Branch names and commits include the Jira key, e.g. `LUMI-12-auth-api`.
- `main` is protected: open a PR, 1 review required.
- Never commit secrets or camera credentials. Use `.env` (copied from `.env.example`).
- No face recognition; store only flagged clips.
