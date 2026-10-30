import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import AuthImage from "../components/AuthImage.jsx";

const TYPES = { checkout: "Checkout", exit: "Exit" };
const NO_SNAPSHOT = "No snapshot yet. Start the edge agent";

const pointsAttr = (points) => points.map(([x, y]) => `${x},${y}`).join(" ");
const at = ([x, y]) => ({ left: `${x * 100}%`, top: `${y * 100}%` });

function centre(polygon) {
  const sum = polygon.reduce(([sx, sy], [x, y]) => [sx + x, sy + y], [0, 0]);
  return [sum[0] / polygon.length, sum[1] / polygon.length];
}

// Clicks become fractions (0..1) of the image, so zones work at any resolution.
function toPoint(e) {
  const box = e.currentTarget.getBoundingClientRect();
  const fraction = (value) => Math.round(Math.min(Math.max(value, 0), 1) * 10000) / 10000;
  return [fraction((e.clientX - box.left) / box.width), fraction((e.clientY - box.top) / box.height)];
}

export default function ZoneEditor() {
  const { id } = useParams();
  const [camera, setCamera] = useState(null);
  const [zones, setZones] = useState([]);
  const [draft, setDraft] = useState([]); // points of the shape being drawn
  const [cursor, setCursor] = useState(null);
  const [type, setType] = useState("checkout");
  const [name, setName] = useState("");
  const [dirty, setDirty] = useState(false);
  const [justSaved, setJustSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let stale = false;
    Promise.all([api.camera(id), api.zones(id)])
      .then(([cameraResult, zoneList]) => {
        if (stale) return;
        setCamera(cameraResult);
        setZones(zoneList);
      })
      .catch((err) => {
        if (!stale) setError(err.message);
      });
    return () => {
      stale = true;
    };
  }, [id]);

  function changeZones(next) {
    setZones(next);
    setDirty(true);
    setJustSaved(false);
  }

  function addPoint(e) {
    if (e.detail > 1) return; // second click of a double-click: onDoubleClick finishes the shape
    const point = toPoint(e);
    setDraft((old) => [...old, point]);
  }

  function finishShape() {
    if (draft.length < 3) return;
    changeZones([...zones, { type, name: name.trim() || null, polygon: draft }]);
    setDraft([]);
    setName("");
  }

  function clearAll() {
    setDraft([]);
    changeZones([]);
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      setZones(await api.saveZones(id, zones.map(({ type, name, polygon }) => ({ type, name, polygon }))));
      setDirty(false);
      setJustSaved(true);
    } catch (err) {
      setError(err.message);
    }
    setSaving(false);
  }

  if (!camera) {
    return (
      <>
        <Link className="back-link" to="/cameras">
          ← Cameras
        </Link>
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

  const missing = Object.keys(TYPES).filter((t) => !zones.some((zone) => zone.type === t));

  return (
    <>
      <Link className="back-link" to="/cameras">
        ← Cameras
      </Link>
      <header className="page-head">
        <div>
          <h1>Zones: {camera.name}</h1>
          <p className="muted">Click to add points. Double-click or press Finish to close the shape.</p>
        </div>
      </header>

      <div className="zones">
        <div className="zone-canvas" onMouseLeave={() => setCursor(null)}>
          {camera.has_snapshot ? (
            <AuthImage
              path={`/cameras/${camera.id}/snapshot`}
              alt={`Latest frame from ${camera.name}`}
              fallback={NO_SNAPSHOT}
            />
          ) : (
            <div className="img-placeholder">{NO_SNAPSHOT}</div>
          )}

          <svg
            viewBox="0 0 1 1"
            preserveAspectRatio="none"
            onClick={addPoint}
            onDoubleClick={finishShape}
            onMouseMove={(e) => setCursor(toPoint(e))}
          >
            {zones.map((zone, i) => (
              <polygon key={i} className={`zone-${zone.type}`} points={pointsAttr(zone.polygon)} />
            ))}
            {draft.length > 0 && (
              <polygon
                className={`zone-${type} zone-draft`}
                points={pointsAttr(cursor ? [...draft, cursor] : draft)}
              />
            )}
          </svg>

          {/* The svg stretches with the image, so round dots and text are drawn as HTML on top of it. */}
          {zones.map((zone, i) => (
            <span key={i} className={`zone-label zone-${zone.type}`} style={at(centre(zone.polygon))}>
              {zone.name || TYPES[zone.type]}
            </span>
          ))}
          {draft.map((point, i) => (
            <span key={i} className={`zone-dot zone-${type}`} style={at(point)} />
          ))}
        </div>

        <aside className="zone-panel">
          <section className="card stack">
            <h2>New zone</h2>
            <div className="segmented" role="radiogroup" aria-label="Zone type">
              {Object.entries(TYPES).map(([value, label]) => (
                <label key={value} className={type === value ? `selected zone-${value}` : ""}>
                  <input
                    type="radio"
                    name="zone-type"
                    value={value}
                    checked={type === value}
                    onChange={() => setType(value)}
                  />
                  {label}
                </label>
              ))}
            </div>
            <label className="field">
              <span>
                Name <span className="muted">(optional)</span>
              </span>
              <input
                maxLength={120}
                placeholder={type === "exit" ? "Main door" : "Till 1"}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <div className="row">
              <button className="btn btn-primary" disabled={draft.length < 3} onClick={finishShape}>
                Finish
              </button>
              <button
                className="btn"
                disabled={draft.length === 0}
                onClick={() => setDraft((old) => old.slice(0, -1))}
              >
                Undo point
              </button>
            </div>
          </section>

          <section className="card stack">
            <h2>Zones ({zones.length})</h2>
            {zones.length === 0 && <p className="muted">Nothing drawn yet.</p>}
            <ul className="zone-list">
              {zones.map((zone, i) => (
                <li key={i}>
                  <span className={`zone-swatch zone-${zone.type}`} aria-hidden="true" />
                  <span className="zone-list-name">
                    {zone.name || TYPES[zone.type]}
                    {zone.name && <span className="muted"> · {TYPES[zone.type]}</span>}
                  </span>
                  <button
                    className="link-button"
                    aria-label={`Delete ${zone.name || TYPES[zone.type]} zone`}
                    onClick={() => changeZones(zones.filter((_, index) => index !== i))}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
            <button className="btn" disabled={zones.length === 0 && draft.length === 0} onClick={clearAll}>
              Clear all
            </button>
          </section>

          {missing.length > 0 && (
            <p className="notice notice-warning">
              Add at least one {missing.map((t) => TYPES[t]).join(" and one ")} zone. The alert rule needs both.
            </p>
          )}
          {draft.length > 0 && <p className="notice notice-warning">Finish or undo the shape you're drawing to save.</p>}
          {error && (
            <p className="notice notice-error" role="alert">
              {error}
            </p>
          )}
          {justSaved && !dirty && <p className="notice notice-success">Zones saved.</p>}

          <button className="btn btn-primary" disabled={saving || !dirty || draft.length > 0} onClick={save}>
            {saving ? "Saving…" : "Save zones"}
          </button>
        </aside>
      </div>
    </>
  );
}
