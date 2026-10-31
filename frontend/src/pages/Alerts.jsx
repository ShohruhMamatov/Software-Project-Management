import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import AuthImage from "../components/AuthImage.jsx";
import ScoreBar from "../components/ScoreBar.jsx";
import { formatTime, percent } from "../utils";

const POLL_MS = 5000;
const FIRST_LOAD_LIMIT = 50;
const alertSound = new Audio("/alert.wav");

function notify(event) {
  if ("Notification" in window && Notification.permission === "granted") {
    new Notification("LUMI: please review", { body: `${event.camera_name} · ${percent(event.score)}` });
  }
}

function AlertCard({ event, onReviewed, onError }) {
  const [busy, setBusy] = useState(false);

  async function review(status) {
    setBusy(true);
    onError("");
    try {
      await api.review(event.id, status);
      onReviewed(event.id);
    } catch (err) {
      onError(err.message);
      setBusy(false);
    }
  }

  return (
    <article className={`card alert-card ${event.isNew ? "alert-new" : ""}`}>
      {event.has_snapshot ? (
        <AuthImage path={`/events/${event.id}/snapshot`} alt={`Snapshot from ${event.camera_name}`} />
      ) : (
        <div className="img-placeholder">No image</div>
      )}
      <div className="alert-body">
        <div className="alert-title">
          <h2>{event.camera_name}</h2>
          <time dateTime={event.started_at}>{formatTime(event.started_at)}</time>
        </div>
        <ScoreBar score={event.score} />
        <div className="alert-actions">
          <Link className="btn btn-primary" to={`/events/${event.id}`}>
            Review
          </Link>
          <button className="btn" disabled={busy} onClick={() => review("confirmed")}>
            Confirm
          </button>
          <button className="btn" disabled={busy} onClick={() => review("dismissed")}>
            Dismiss
          </button>
        </div>
      </div>
    </article>
  );
}

export default function Alerts() {
  const [events, setEvents] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [olderCount, setOlderCount] = useState(0);
  const [connected, setConnected] = useState(true);
  const [soundBlocked, setSoundBlocked] = useState(false);
  const [error, setError] = useState("");
  const lastId = useRef(null); // highest pending id seen; null until the first successful load

  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();
    let stopped = false;
    let timer;

    async function load() {
      try {
        const firstLoad = lastId.current === null;
        const params = lastId.current
          ? { status: "pending", after_id: lastId.current }
          : { status: "pending", limit: FIRST_LOAD_LIMIT };
        const { items, total } = await api.events(params);
        if (stopped) return; // effect was cleaned up while the request was running

        if (items.length) {
          if (!firstLoad) {
            alertSound.currentTime = 0;
            alertSound.play().catch(() => setSoundBlocked(true)); // browsers block sound until the user clicked once
            items.forEach(notify);
          }
          lastId.current = Math.max(lastId.current ?? 0, ...items.map((e) => e.id));
          setEvents((old) => [...items.map((e) => ({ ...e, isNew: !firstLoad })), ...old]);
        } else if (firstLoad) {
          lastId.current = 0;
        }
        if (firstLoad) setOlderCount(total - items.length);
        setLoaded(true);
        setConnected(true);
      } catch {
        if (stopped) return;
        setConnected(false);
      }
      timer = setTimeout(load, POLL_MS);
    }

    load();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, []);

  function enableSound() {
    setSoundBlocked(false);
    alertSound.play().catch(() => setSoundBlocked(true));
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Live alerts</h1>
          <p className="muted">Suspicious activity — please review.</p>
        </div>
        <span className={`live ${connected ? "" : "live-off"}`}>{connected ? "Live" : "Offline"}</span>
      </header>

      {!connected && (
        <p className="notice notice-error" role="alert">
          Connection lost, retrying…
        </p>
      )}
      {soundBlocked && (
        <p className="notice notice-warning">
          Your browser blocked the alert sound.{" "}
          <button className="link-button" onClick={enableSound}>
            Turn sound on
          </button>
        </p>
      )}
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}

      {loaded && events.length === 0 && (
        <div className="card empty">
          <h2>No alerts to review 🎉</h2>
          <p className="muted">New alerts appear here automatically, with a sound.</p>
        </div>
      )}
      {!loaded && connected && <p className="muted">Loading…</p>}

      <div className="alert-grid">
        {events.map((event) => (
          <AlertCard
            key={event.id}
            event={event}
            onError={setError}
            onReviewed={(id) => setEvents((old) => old.filter((e) => e.id !== id))}
          />
        ))}
      </div>

      {olderCount > 0 && (
        <p className="muted list-foot">
          {olderCount} older pending {olderCount === 1 ? "alert is" : "alerts are"} not shown here.{" "}
          <Link to="/events?status=pending">See all in the event log</Link>
        </p>
      )}
    </>
  );
}
