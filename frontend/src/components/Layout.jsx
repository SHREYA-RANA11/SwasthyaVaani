import { Link } from 'react-router-dom';
import { useAuth } from '../useAuth';

const ROLE_LABEL = {
  patient: 'Patient',
  healthcare_worker: 'Healthcare Worker',
  admin: 'Administrator',
};

// Shared shell. nav items: { id, label } scroll to a section, { to, label } go to a page.
export default function Layout({ nav, title, children }) {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">+</span> SwasthyaVaani
        </div>
        <nav>
          {nav.map((n) =>
            n.to ? (
              <Link key={n.to} to={n.to}>{n.label}</Link>
            ) : (
              <a key={n.id} href={`#${n.id}`}>{n.label}</a>
            )
          )}
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <h1>{title}</h1>
          <div className="user-chip">
            <div>
              <strong>{user.full_name}</strong>
              <span className="badge">{ROLE_LABEL[user.role]}</span>
            </div>
            <button className="btn btn-ghost" onClick={logout}>Log out</button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
