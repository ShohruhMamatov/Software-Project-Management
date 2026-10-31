import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import ScoreBar from "../components/ScoreBar.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { formatTime } from "../utils";

const PAGE_SIZE = 50;
const STATUSES = ["pending", "confirmed", "dismissed"];

export default function Events() {
  // Filters live in the URL, so coming back from an event keeps the same view.
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const cameraId = params.get("camera") ?? "";
  const page = Math.max(Number(params.get("page")) || 1, 1);

  const [data, setData] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.cameras().then(setCameras).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    let stale = false;
    api
      .events({ status, camera_id: cameraId, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
      .then((result) => {
        if (stale) return;
        setData(result);
        setError("");
      })
      .catch((err) => {
        if (!stale) setError(err.message);
      });
    return () => {
      stale = true;
    };
  }, [status, cameraId, page]);

  function setParam(name, value) {
    const next = new URLSearchParams(params);
    if (name !== "page") next.delete("page"); // a new filter starts from the first page
    if (value) next.set(name, value);
    else next.delete(name);
    setParams(next);
  }

  const lastPage = data ? Math.max(Math.ceil(data.total / PAGE_SIZE), 1) : 1;
  const firstRow = (page - 1) * PAGE_SIZE + 1;

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Event log</h1>
          <p className="muted">Every flagged event and how it was reviewed.</p>
        </div>
      </header>

      <div className="filters">
        <label className="field-inline">
          Status
          <select value={status} onChange={(e) => setParam("status", e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s[0].toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </label>
        <label className="field-inline">
          Camera
          <select value={cameraId} onChange={(e) => setParam("camera", e.target.value)}>
            <option value="">All</option>
            {cameras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
      {!data && !error && <p className="muted">Loading…</p>}

      {data && data.items.length === 0 && (
        <div className="card empty">
          <h2>No events found</h2>
          <p className="muted">{status || cameraId ? "Try different filters." : "Flagged events will be listed here."}</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="card table-card">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Camera</th>
                  <th>Score</th>
                  <th>Status</th>
                  <th>Reviewed at</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((event) => (
                  <tr
                    key={event.id}
                    onClick={(e) => {
                      if (!e.target.closest("a")) navigate(`/events/${event.id}`);
                    }}
                  >
                    <td>
                      <Link to={`/events/${event.id}`}>{formatTime(event.started_at)}</Link>
                    </td>
                    <td>{event.camera_name}</td>
                    <td className="cell-score">
                      <ScoreBar score={event.score} />
                    </td>
                    <td>
                      <StatusBadge status={event.status} />
                    </td>
                    <td className="muted">{formatTime(event.reviewed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <span className="muted">
              {firstRow}–{firstRow + data.items.length - 1} of {data.total}
            </span>
            <button className="btn" disabled={page <= 1} onClick={() => setParam("page", String(page - 1))}>
              Previous
            </button>
            <button className="btn" disabled={page >= lastPage} onClick={() => setParam("page", String(page + 1))}>
              Next
            </button>
          </div>
        </>
      )}
    </>
  );
}
