// The centred card used by the login and register pages.
export default function AuthCard({ title, subtitle, children }) {
  return (
    <main className="center-page">
      <div className="card auth-card">
        <div className="auth-brand">
          <span className="brand-mark" aria-hidden="true" />
          LUMI
        </div>
        <h1>{title}</h1>
        <p className="muted">{subtitle}</p>
        {children}
      </div>
    </main>
  );
}
