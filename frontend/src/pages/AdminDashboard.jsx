import { useEffect, useState } from 'react';
import API, { errorMessage } from '../api';
import { useAuth } from '../useAuth';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import SampleTag from '../components/SampleTag';

const NAV = [
  { id: 'overview', label: 'Overview' },
  { id: 'users', label: 'User management' },
  { id: 'content', label: 'Content management' },
  { id: 'system', label: 'System status' },
];

const CONTENT = [
  { id: 1, title: 'Preventing malaria', lang: 'Hindi', status: 'Published' },
  { id: 2, title: 'Newborn care basics', lang: 'Gujarati', status: 'Draft' },
  { id: 3, title: 'Managing diabetes', lang: 'English', status: 'Published' },
];

export default function AdminDashboard() {
  const { user: me } = useAuth();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [role, setRole] = useState('');
  const [error, setError] = useState('');
  const [health, setHealth] = useState('checking…');

  const [version, setVersion] = useState(0); // bump to reload the data

  useEffect(() => {
    Promise.all([
      API.get('/admin/stats'),
      API.get('/admin/users', { params: role ? { role } : {} }),
    ])
      .then(([s, u]) => {
        setStats(s.data);
        setUsers(u.data);
        setError('');
      })
      .catch((err) => setError(errorMessage(err)));
  }, [role, version]);

  useEffect(() => {
    API.get('/health')
      .then((r) => setHealth(r.data.status))
      .catch(() => setHealth('unreachable'));
  }, []);

  async function toggleActive(u) {
    try {
      await API.patch(`/admin/users/${u.id}/active`, { is_active: !u.is_active });
      setVersion((v) => v + 1);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const roleName = { patient: 'Patients', healthcare_worker: 'Healthcare workers', admin: 'Admins' };

  return (
    <Layout nav={NAV} title="Admin Dashboard">
      {error && <div className="alert alert-err">{error}</div>}

      <section id="overview">
        <div className="grid stats">
          <StatCard label="Total users" value={stats?.total_users ?? '…'} />
          <StatCard label="Active" value={stats?.active_users ?? '…'} />
          <StatCard label="Inactive" value={stats?.inactive_users ?? '…'} />
          <StatCard label="Patients" value={stats?.by_role?.patient ?? '…'} />
          <StatCard label="Prescriptions" value={stats?.total_prescriptions ?? '…'} />
          <StatCard label="Awaiting review" value={stats?.prescriptions_needing_review ?? '…'} />
        </div>

        {stats && (
          <div className="grid two">
            <div className="card">
              <h2>Users by role</h2>
              {Object.entries(stats.by_role).map(([r, n]) => (
                <Bar key={r} label={roleName[r] || r} value={n} total={stats.total_users} />
              ))}
            </div>
            <div className="card">
              <h2>Users by language</h2>
              {Object.entries(stats.by_language).map(([l, n]) => (
                <Bar key={l} label={l} value={n} total={stats.total_users} />
              ))}
            </div>
          </div>
        )}
      </section>

      <section id="users" className="card">
        <div className="row-between">
          <h2>User management</h2>
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="">All roles</option>
            <option value="patient">Patients</option>
            <option value="healthcare_worker">Healthcare workers</option>
            <option value="admin">Admins</option>
          </select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>{roleName[u.role] || u.role}</td>
                  <td><span className={`badge ${u.is_active ? 'ok' : 'off'}`}>{u.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td>
                    {u.id !== me.id && (
                      <button className="btn btn-ghost" onClick={() => toggleActive(u)}>
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="content" className="card">
        <div className="row-between">
          <h2>Content management <SampleTag /></h2>
          <button className="btn btn-primary" disabled>New article (coming soon)</button>
        </div>
        <ul className="list">
          {CONTENT.map((c) => (
            <li key={c.id}>
              <div><strong>{c.title}</strong><div className="muted">{c.lang}</div></div>
              <span className="badge">{c.status}</span>
            </li>
          ))}
        </ul>
      </section>

      <section id="system" className="card">
        <h2>System status</h2>
        <p>API: <span className={`badge ${health === 'healthy' ? 'ok' : 'off'}`}>{health}</span></p>
      </section>
    </Layout>
  );
}

function Bar({ label, value, total }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <div className="bar">
      <div className="row-between"><span>{label}</span><span className="muted">{value}</span></div>
      <div className="bar-track"><div className="bar-fill" style={{ width: `${pct}%` }} /></div>
    </div>
  );
}
