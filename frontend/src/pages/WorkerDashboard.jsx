import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useCachedGet } from '../useCachedGet';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import SampleTag from '../components/SampleTag';

const NAV = [
  { id: 'review', label: 'Needs review' },
  { id: 'prescriptions', label: 'Recent prescriptions' },
  { id: 'patients', label: 'Patients' },
  { id: 'followups', label: 'Follow-ups' },
];

const FOLLOWUPS = [
  { id: 1, text: 'Check fever recovery', due: 'Tomorrow' },
  { id: 2, text: 'Review medicine adherence', due: 'In 3 days' },
  { id: 3, text: 'Prenatal check-up reminder', due: 'Next week' },
];

function RxTable({ rows, empty }) {
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Patient</th><th>Prescription</th><th>Language</th><th>Status</th><th></th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.patient_name}</td>
              <td>{r.title}</td>
              <td>{r.language}</td>
              <td>
                {r.status === 'failed' && <span className="badge off">Could not read</span>}
                {r.status === 'processed' && r.needs_review && <span className="badge off">Needs review</span>}
                {r.status === 'processed' && !r.needs_review && r.reviewed_at && <span className="badge ok">Verified</span>}
                {r.status === 'processed' && !r.needs_review && !r.reviewed_at && <span className="badge">AI only</span>}
              </td>
              <td><Link className="btn btn-ghost" to={`/prescriptions/${r.id}`}>Open</Link></td>
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan="5" className="muted">{empty}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export default function WorkerDashboard() {
  const patients = useCachedGet('/users/patients');
  const queue = useCachedGet('/prescriptions', { params: { needs_review: true }, cacheKey: 'rx-review' });
  const recent = useCachedGet('/prescriptions', { cacheKey: 'rx-all' });
  const [query, setQuery] = useState('');

  const list = useMemo(() => patients.data || [], [patients.data]);
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? list.filter((p) => p.full_name.toLowerCase().includes(q) || p.email.toLowerCase().includes(q)) : list;
  }, [list, query]);

  return (
    <Layout nav={NAV} title="Healthcare Worker Dashboard">
      <div className="grid stats">
        <StatCard label="Registered patients" value={patients.data ? list.length : '…'} />
        <StatCard label="Awaiting your review" value={queue.data ? queue.data.length : '…'} />
        <StatCard label="Prescriptions uploaded" value={recent.data ? recent.data.length : '…'} />
        <StatCard label="Pending follow-ups" value={FOLLOWUPS.length} hint="sample" />
      </div>

      <section id="review" className="card">
        <h2>Needs review</h2>
        <p className="muted">The AI was not sure about these. Compare each with the original and verify it, or tell the patient to see a doctor.</p>
        {queue.error && <div className="alert alert-err">{queue.error}</div>}
        <RxTable rows={queue.data || []} empty="Nothing waiting for review. 🎉" />
      </section>

      <section id="prescriptions" className="card">
        <h2>Recent prescriptions</h2>
        {recent.error && <div className="alert alert-err">{recent.error}</div>}
        <RxTable rows={(recent.data || []).slice(0, 20)} empty="No prescriptions uploaded yet." />
      </section>

      <section id="patients" className="card">
        <div className="row-between">
          <h2>Patients</h2>
          <input className="search" placeholder="Search name or email…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        {patients.error && <div className="alert alert-err">{patients.error}</div>}
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Language</th></tr></thead>
            <tbody>
              {shown.map((p) => (
                <tr key={p.id}><td>{p.full_name}</td><td>{p.email}</td><td>{p.phone || '—'}</td><td>{p.preferred_language}</td></tr>
              ))}
              {shown.length === 0 && <tr><td colSpan="4" className="muted">No patients found.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section id="followups" className="card">
        <h2>Follow-ups <SampleTag /></h2>
        <ul className="list">
          {FOLLOWUPS.map((f) => (
            <li key={f.id}><span>{f.text}</span><span className="badge">{f.due}</span></li>
          ))}
        </ul>
      </section>
    </Layout>
  );
}
