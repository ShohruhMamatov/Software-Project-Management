# frontend

React + Vite dashboard: login/register, store setup, live alerts, event log, review (confirm/dismiss), cameras & zones.

Full MVP spec (screens, API, polling, zone editor): [docs/frontend-spec.md](../docs/frontend-spec.md)

## Run it

Start the backend first (see the [root README](../README.md); API on http://localhost:8000), then:

```bash
cd frontend
cp .env.example .env      # Windows PowerShell: copy .env.example .env
npm install
npm run dev               # http://localhost:5173
```

The backend only allows requests from `http://localhost:5173`, so the dev server refuses to start on another port.
To use a different one, add it to `CORS_ORIGINS` in the root `.env` and change `server.port` in `vite.config.js`.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Lint with oxlint |

## Test data without a camera

`scripts/send_test_event.py` plays the edge agent. Copy the API key shown when you create the store, then from the
repo root:

```powershell
python scripts/send_test_event.py --api-key lumi_xxx --camera-id 1 --heartbeat-only --snapshot frame.jpg   # camera online + zone editor background
python scripts/send_test_event.py --api-key lumi_xxx --camera-id 1 --snapshot frame.jpg --clip clip.webm   # new alert
```

## Where things are

```
src/
  api.js        fetch wrapper + all API calls
  auth.jsx      AuthContext: user, login(), logout()
  App.jsx       routes, route guards and the sidebar layout
  utils.js      time/score formatting, login checks, RTSP preview
  index.css     all styles
  pages/        one file per screen
  components/   AuthImage/AuthVideo (media that needs the token), badges, modal
public/
  alert.wav     sound for new alerts
```
