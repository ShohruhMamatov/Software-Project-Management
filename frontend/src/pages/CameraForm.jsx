import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { rtspPreview } from "../utils";

const DEFAULTS = {
  name: "",
  ip: "",
  port: 554,
  channel: 1,
  rtsp_username: "admin",
  rtsp_password: "",
  threshold: 0.5,
  is_active: true,
};

// PATCH only what changed. rtsp_password is never returned, so typing nothing keeps the current one.
const changedFields = (form, camera) =>
  Object.fromEntries(Object.entries(form).filter(([field, value]) => value !== (camera[field] ?? "")));

export default function CameraForm() {
  const { id } = useParams();
  const editing = id !== undefined;
  const [form, setForm] = useState(DEFAULTS);
  const [camera, setCamera] = useState(null);
  const [saved, setSaved] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!editing) return;
    let stale = false;
    api
      .camera(id)
      .then((result) => {
        if (stale) return;
        setCamera(result);
        setForm(Object.fromEntries(Object.keys(DEFAULTS).map((field) => [field, result[field] ?? ""])));
      })
      .catch((err) => {
        if (!stale) setError(err.message);
      });
    return () => {
      stale = true;
    };
  }, [editing, id]);

  const set = (field) => (e) => {
    const { type, checked, value } = e.target;
    setForm((old) => ({ ...old, [field]: type === "checkbox" ? checked : value }));
  };

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const values = {
      ...form,
      name: form.name.trim(),
      ip: form.ip.trim(),
      rtsp_username: form.rtsp_username.trim(),
      port: Number(form.port),
      channel: Number(form.channel),
      threshold: Number(form.threshold),
    };
    try {
      setSaved(editing ? await api.updateCamera(id, changedFields(values, camera)) : await api.createCamera(values));
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  if (saved) {
    return (
      <div className="narrow">
        <section className="card stack">
          <h1>{saved.name} saved</h1>
          <p className="muted">The camera turns Online once the in-store agent connects to it.</p>
          <div className="row">
            <Link className="btn btn-primary" to={`/cameras/${saved.id}/zones`}>
              Draw zones
            </Link>
            <Link className="btn" to="/cameras">
              Back to cameras
            </Link>
          </div>
        </section>
      </div>
    );
  }

  if (editing && !camera) {
    return error ? (
      <p className="notice notice-error" role="alert">
        {error}
      </p>
    ) : (
      <p className="muted">Loading…</p>
    );
  }

  return (
    <div className="narrow">
      <Link className="back-link" to="/cameras">
        ← Cameras
      </Link>
      <header className="page-head">
        <div>
          <h1>{editing ? `Edit ${camera.name}` : "Add camera"}</h1>
          <p className="muted">Find the camera IP with Hikvision's SADP tool. RTSP must be enabled on the camera.</p>
        </div>
      </header>

      <form className="card form-grid" onSubmit={submit}>
        <label className="field span-2">
          Name
          <input
            required
            autoFocus={!editing}
            maxLength={120}
            placeholder="Entrance"
            value={form.name}
            onChange={set("name")}
          />
        </label>
        <label className="field span-2">
          IP address
          <input required maxLength={64} placeholder="192.168.1.64" value={form.ip} onChange={set("ip")} />
        </label>
        <label className="field">
          RTSP port
          <input type="number" required min={1} max={65535} value={form.port} onChange={set("port")} />
        </label>
        <label className="field">
          Channel
          <input type="number" required min={1} max={64} value={form.channel} onChange={set("channel")} />
          <span className="hint">NVR channel number. A single camera is 1.</span>
        </label>
        <label className="field">
          RTSP username
          <input required maxLength={64} autoComplete="off" value={form.rtsp_username} onChange={set("rtsp_username")} />
        </label>
        <label className="field">
          RTSP password
          <input
            type="password"
            required={!editing}
            maxLength={128}
            autoComplete="new-password"
            value={form.rtsp_password}
            onChange={set("rtsp_password")}
          />
          {editing && <span className="hint">Leave empty to keep the current password.</span>}
        </label>
        <label className="field span-2">
          <span className="slider-label">
            Sensitivity <strong>{Number(form.threshold).toFixed(2)}</strong>
          </span>
          <input type="range" min={0} max={1} step={0.05} value={form.threshold} onChange={set("threshold")} />
          <span className="slider-scale">
            <span>Lower: more alerts</span>
            <span>Higher: fewer alerts</span>
          </span>
        </label>
        <label className="toggle span-2">
          <input type="checkbox" checked={form.is_active} onChange={set("is_active")} />
          Active <span className="muted">(inactive cameras are ignored by the edge agent)</span>
        </label>

        <div className="rtsp-preview span-2">
          <span className="hint">Sub-stream (used for detection)</span>
          <code className="rtsp">{rtspPreview(form, "02")}</code>
          <span className="hint">Main stream</span>
          <code className="rtsp">{rtspPreview(form, "01")}</code>
        </div>

        {error && (
          <p className="notice notice-error span-2" role="alert">
            {error}
          </p>
        )}
        <div className="row span-2">
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Saving…" : editing ? "Save changes" : "Add camera"}
          </button>
          <Link className="btn" to="/cameras">
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
