import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { api } from "../api";
import ConfirmModal from "../components/ConfirmModal.jsx";
import { timeAgo } from "../utils";

const REFRESH_MS = 15000; // keeps the Online/Offline badges current

function CameraCard({ camera, isOwner, onToggle, onDelete }) {
  return (
    <article className="card camera-card">
      <div className="camera-head">
        <h2>{camera.name}</h2>
        <span className={`badge ${camera.online ? "badge-online" : "badge-offline"}`}>
          {camera.online ? "Online" : "Offline"}
        </span>
      </div>
      <p className="muted">Last seen: {timeAgo(camera.last_seen_at)}</p>
      <code className="rtsp">{camera.rtsp_url_sub}</code>
      <div className="camera-meta">
        <span>
          Sensitivity threshold: <strong>{camera.threshold.toFixed(2)}</strong>
        </span>
        {isOwner ? (
          <label className="toggle">
            <input type="checkbox" checked={camera.is_active} onChange={() => onToggle(camera)} />
            Active
          </label>
        ) : (
          <span>{camera.is_active ? "Active" : "Inactive"}</span>
        )}
      </div>
      {isOwner && (
        <div className="camera-actions">
          <Link className="btn" to={`/cameras/${camera.id}/zones`}>
            Zones
          </Link>
          <Link className="btn" to={`/cameras/${camera.id}/edit`}>
            Edit
          </Link>
          <button className="btn btn-danger-quiet" onClick={() => onDelete(camera)}>
            Delete
          </button>
        </div>
      )}
    </article>
  );
}

export default function Cameras() {
  const { isOwner } = useAuth();
  const [cameras, setCameras] = useState(null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  useEffect(() => {
    let stale = false;
    function load() {
      api
        .cameras()
        .then((list) => {
          if (stale) return;
          setCameras(list);
          setError("");
        })
        .catch((err) => {
          if (!stale) setError(err.message);
        });
    }
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      stale = true;
      clearInterval(timer);
    };
  }, []);

  async function toggleActive(camera) {
    setError("");
    try {
      const updated = await api.updateCamera(camera.id, { is_active: !camera.is_active });
      setCameras((old) => old.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err) {
      setError(err.message);
    }
  }

  async function confirmDelete() {
    setDeleteBusy(true);
    setDeleteError("");
    try {
      await api.deleteCamera(deleting.id);
      setCameras((old) => old.filter((c) => c.id !== deleting.id));
      setDeleting(null);
    } catch (err) {
      setDeleteError(err.message);
    }
    setDeleteBusy(false);
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Cameras</h1>
          <p className="muted">The in-store agent reads these cameras and reports their status.</p>
        </div>
        {isOwner && (
          <Link className="btn btn-primary" to="/cameras/new">
            Add camera
          </Link>
        )}
      </header>

      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
      {!cameras && !error && <p className="muted">Loading…</p>}

      {cameras?.length === 0 && (
        <div className="card empty">
          <h2>Add your first Hikvision camera</h2>
          <p className="muted">
            {isOwner
              ? "Enter its IP address and login, then draw the checkout and exit zones."
              : "The store owner hasn't added any cameras yet."}
          </p>
          {isOwner && (
            <Link className="btn btn-primary" to="/cameras/new">
              Add camera
            </Link>
          )}
        </div>
      )}

      <div className="camera-grid">
        {cameras?.map((camera) => (
          <CameraCard
            key={camera.id}
            camera={camera}
            isOwner={isOwner}
            onToggle={toggleActive}
            onDelete={setDeleting}
          />
        ))}
      </div>

      {deleting && (
        <ConfirmModal
          title={`Delete ${deleting.name}?`}
          confirmLabel="Delete camera"
          danger
          busy={deleteBusy}
          error={deleteError}
          onConfirm={confirmDelete}
          onCancel={() => {
            setDeleting(null);
            setDeleteError("");
          }}
        >
          <p>This also deletes its zones and all of its events, clips and snapshots. This can't be undone.</p>
        </ConfirmModal>
      )}
    </>
  );
}
