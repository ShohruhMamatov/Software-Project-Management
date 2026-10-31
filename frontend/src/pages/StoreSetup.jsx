import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { api } from "../api";
import ApiKeyBox from "../components/ApiKeyBox.jsx";

export default function StoreSetup() {
  const { user, updateUser } = useAuth();
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [created, setCreated] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // `created` keeps this page open after POST /stores: the API key is shown only this once.
  if (user.store_id !== null && !created) return <Navigate to="/alerts" replace />;

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const store = await api.createStore({ name: name.trim(), address: address.trim() || undefined });
      setCreated(store);
      updateUser({ store_id: store.id });
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  if (created) {
    return (
      <div className="narrow">
        <header className="page-head">
          <div>
            <h1>{created.name} is ready</h1>
          </div>
        </header>
        <section className="card stack">
          <h2>Edge agent API key</h2>
          <ApiKeyBox apiKey={created.api_key} />
          <p className="notice notice-warning">
            Save this key. The in-store edge agent needs it. You can generate a new one in Settings.
          </p>
          <Link className="btn btn-primary" to="/cameras">
            Continue
          </Link>
        </section>
      </div>
    );
  }

  return (
    <div className="narrow">
      <header className="page-head">
        <div>
          <h1>Set up your store</h1>
          <p className="muted">One store per account. You can change these details later in Settings.</p>
        </div>
      </header>
      <form className="card stack" onSubmit={submit}>
        <label className="field">
          Store name
          <input required autoFocus maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="field">
          <span>
            Address <span className="muted">(optional)</span>
          </span>
          <input maxLength={255} value={address} onChange={(e) => setAddress(e.target.value)} />
        </label>
        {error && (
          <p className="notice notice-error" role="alert">
            {error}
          </p>
        )}
        <button className="btn btn-primary" disabled={busy || !name.trim()}>
          {busy ? "Creating store…" : "Create store"}
        </button>
      </form>
    </div>
  );
}
