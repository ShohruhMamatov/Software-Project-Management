import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import AuthImage from "../components/AuthImage.jsx";
import AuthVideo from "../components/AuthVideo.jsx";
import ScoreBar from "../components/ScoreBar.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { formatTime } from "../utils";

// Returns to wherever the user came from (alerts or a filtered event log); /alerts on a direct visit.
function BackLink() {
  const navigate = useNavigate();
  const { key } = useLocation();
  return (
    <Link
      className="back-link"
      to="/alerts"
      onClick={(e) => {
        if (key === "default") return;
        e.preventDefault();
        navigate(-1);
      }}
    >
      ← Back
    </Link>
  );
}

function Snapshot({ event }) {
  if (!event.has_snapshot) return <div className="img-placeholder">No clip or snapshot for this event</div>;
  return <AuthImage path={`/events/${event.id}/snapshot`} alt={`Snapshot from ${event.camera_name}`} />;
}

function Review({ id }) {
  const [event, setEvent] = useState(null);
  const [nextId, setNextId] = useState(undefined); // undefined = not reviewed yet, null = nothing left
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let stale = false;
    api
      .event(id)
      .then((result) => {
        if (!stale) setEvent(result);
      })
      .catch((err) => {
        if (!stale) setError(err.message);
      });
    return () => {
      stale = true;
    };
  }, [id]);

  async function review(status) {
    setBusy(true);
    setError("");
    try {
      setEvent(await api.review(id, status));
      const { items } = await api.events({ status: "pending", limit: 1 });
      setNextId(items[0]?.id ?? null);
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  if (!event) {
    return (
      <>
        <BackLink />
        {error ? (
          <p className="notice notice-error" role="alert">
            {error}
          </p>
        ) : (
          <p className="muted">Loading…</p>
        )}
      </>
    );
  }

  return (
    <>
      <BackLink />
      <header className="page-head">
        <div>
          <h1>Suspicious activity — please review</h1>
          <p className="muted">
            {event.camera_name} · {formatTime(event.started_at)}
          </p>
        </div>
        <StatusBadge status={event.status} />
      </header>

      <div className="review">
        <div className="review-media">
          {event.has_clip ? (
            <AuthVideo path={`/events/${event.id}/clip`} fallback={<Snapshot event={event} />} />
          ) : (
            <Snapshot event={event} />
          )}
        </div>

        <aside className="card stack">
          <dl className="details">
            <dt>Camera</dt>
            <dd>{event.camera_name}</dd>
            <dt>Time</dt>
            <dd>{formatTime(event.started_at)}</dd>
            <dt>Score</dt>
            <dd>
              <ScoreBar score={event.score} />
            </dd>
            <dt>Status</dt>
            <dd>
              <StatusBadge status={event.status} />
            </dd>
            <dt>Reviewed at</dt>
            <dd>{formatTime(event.reviewed_at)}</dd>
          </dl>

          {error && (
            <p className="notice notice-error" role="alert">
              {error}
            </p>
          )}

          <div className="review-actions">
            <button className="btn btn-danger" disabled={busy} onClick={() => review("confirmed")}>
              Confirm (suspicious)
            </button>
            <button className="btn" disabled={busy} onClick={() => review("dismissed")}>
              Dismiss (false alarm)
            </button>
          </div>
          <p className="hint">LUMI flags behaviour for review. It does not identify or accuse anyone.</p>

          {nextId === null && <p className="notice notice-success">No more alerts to review 🎉</p>}
          {nextId && (
            <Link className="btn btn-primary" to={`/events/${nextId}`}>
              Next pending alert →
            </Link>
          )}
        </aside>
      </div>
    </>
  );
}

export default function EventReview() {
  const { id } = useParams();
  return <Review key={id} id={id} />; // "Next pending alert" starts from a clean state
}
