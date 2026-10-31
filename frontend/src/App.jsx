import { NavLink, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Alerts from "./pages/Alerts.jsx";
import CameraForm from "./pages/CameraForm.jsx";
import Cameras from "./pages/Cameras.jsx";
import EventReview from "./pages/EventReview.jsx";
import Events from "./pages/Events.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Settings from "./pages/Settings.jsx";
import StoreSetup from "./pages/StoreSetup.jsx";
import ZoneEditor from "./pages/ZoneEditor.jsx";

const NAV = [
  { to: "/alerts", label: "Alerts" },
  { to: "/events", label: "Events" },
  { to: "/cameras", label: "Cameras" },
  { to: "/settings", label: "Settings" },
];

function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          LUMI
        </div>
        {user.store_id !== null && (
          <nav className="nav">
            {NAV.map(({ to, label }) => (
              <NavLink key={to} to={to}>
                {label}
              </NavLink>
            ))}
          </nav>
        )}
        <div className="sidebar-foot">
          <span className="sidebar-email" title={user.email}>
            {user.email}
          </span>
          <button className="sidebar-logout" onClick={logout}>
            Log out
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

function PublicOnly() {
  const { user } = useAuth();
  if (!user) return <Outlet />;
  return <Navigate to={user.store_id === null ? "/setup" : "/alerts"} replace />;
}

function RequireAuth() {
  const { user } = useAuth();
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}

function RequireStore() {
  const { user } = useAuth();
  return user.store_id === null ? <Navigate to="/setup" replace /> : <Outlet />;
}

function RequireOwner() {
  const { isOwner } = useAuth();
  return isOwner ? <Outlet /> : <Navigate to="/cameras" replace />;
}

export default function App() {
  const { checking, loadError, retry } = useAuth();

  if (checking) {
    return (
      <main className="center-page">
        <p className="muted">Loading…</p>
      </main>
    );
  }
  if (loadError) {
    return (
      <main className="center-page">
        <div className="card auth-card">
          <h1>LUMI is unavailable</h1>
          <p className="notice notice-error" role="alert">
            {loadError}
          </p>
          <button className="btn btn-primary" onClick={retry}>
            Try again
          </button>
        </div>
      </main>
    );
  }

  return (
    <Routes>
      <Route element={<PublicOnly />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/setup" element={<StoreSetup />} />
          <Route element={<RequireStore />}>
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/events" element={<Events />} />
            <Route path="/events/:id" element={<EventReview />} />
            <Route path="/cameras" element={<Cameras />} />
            <Route path="/settings" element={<Settings />} />
            <Route element={<RequireOwner />}>
              <Route path="/cameras/new" element={<CameraForm />} />
              <Route path="/cameras/:id/edit" element={<CameraForm />} />
              <Route path="/cameras/:id/zones" element={<ZoneEditor />} />
            </Route>
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/alerts" replace />} />
    </Routes>
  );
}
