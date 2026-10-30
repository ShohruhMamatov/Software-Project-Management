import { useEffect, useState } from "react";
import { useAuth } from "../auth.jsx";
import { api } from "../api";
import ApiKeyBox from "../components/ApiKeyBox.jsx";
import ConfirmModal from "../components/ConfirmModal.jsx";

export default function Settings() {
  const { user, isOwner } = useAuth();
  const [store, setStore] = useState(null);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [askRotate, setAskRotate] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [rotateError, setRotateError] = useState("");
  const [newKey, setNewKey] = useState("");

  useEffect(() => {
    let stale = false;
    api
      .myStore()
      .then((result) => {
        if (stale) return;
        setStore(result);
        setName(result.name);
        setAddress(result.address ?? "");
      })
      .catch((err) => {
        if (!stale) setError(err.message);
      });
    return () => {
      stale = true;
    };
  }, []);

  async function saveStore(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      setStore(await api.updateStore({ name: name.trim(), address: address.trim() || null }));
      setSaved(true);
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  async function rotateKey() {
    setRotating(true);
    setRotateError("");
    try {
      const { api_key } = await api.rotateApiKey();
      setNewKey(api_key);
      setAskRotate(false);
    } catch (err) {
      setRotateError(err.message);
    }
    setRotating(false);
  }

  return (
    <div className="narrow">
      <header className="page-head">
        <div>
          <h1>Settings</h1>
        </div>
      </header>

      {!store && !error && <p className="muted">Loading…</p>}
      {!store && error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}

      <div className="stack">
        {store && (
          <form className="card stack" onSubmit={saveStore}>
            <h2>Store</h2>
            <label className="field">
              Store name
              <input
                required
                readOnly={!isOwner}
                maxLength={120}
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setSaved(false);
                }}
              />
            </label>
            <label className="field">
              Address
              <input
                readOnly={!isOwner}
                maxLength={255}
                value={address}
                onChange={(e) => {
                  setAddress(e.target.value);
                  setSaved(false);
                }}
              />
            </label>
            {error && (
              <p className="notice notice-error" role="alert">
                {error}
              </p>
            )}
            {saved && <p className="notice notice-success">Store details saved.</p>}
            {isOwner && (
              <div className="row">
                <button className="btn btn-primary" disabled={busy || !name.trim()}>
                  {busy ? "Saving…" : "Save changes"}
                </button>
              </div>
            )}
          </form>
        )}

        {store && isOwner && (
          <section className="card stack">
            <h2>Edge agent API key</h2>
            <p className="muted">The in-store edge agent uses this key to send events to LUMI.</p>
            {newKey ? (
              <>
                <ApiKeyBox apiKey={newKey} />
                <p className="notice notice-warning">Save this key now. It won't be shown again.</p>
              </>
            ) : (
              <div className="row">
                <button className="btn" onClick={() => setAskRotate(true)}>
                  Generate new API key
                </button>
              </div>
            )}
          </section>
        )}

        <section className="card stack">
          <h2>Account</h2>
          <dl className="details">
            <dt>Email</dt>
            <dd>{user.email}</dd>
            {user.full_name && (
              <>
                <dt>Name</dt>
                <dd>{user.full_name}</dd>
              </>
            )}
            <dt>Role</dt>
            <dd>{user.role === "owner" ? "Owner" : "Staff"}</dd>
          </dl>
        </section>
      </div>

      {askRotate && (
        <ConfirmModal
          title="Generate a new API key?"
          confirmLabel="Generate new key"
          danger
          busy={rotating}
          error={rotateError}
          onConfirm={rotateKey}
          onCancel={() => {
            setAskRotate(false);
            setRotateError("");
          }}
        >
          <p>The old key stops working immediately; the edge agent must be updated.</p>
        </ConfirmModal>
      )}
    </div>
  );
}
