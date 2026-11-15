import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import API, { errorMessage } from '../api';
import { useAuth } from '../useAuth';
import { useCachedGet } from '../useCachedGet';
import { useReminders } from '../useReminders';
import { hasVoice, speak, speechSupported } from '../speech';
import { localDate, localTime, prettyTime } from '../time';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import OfflineBanner from '../components/OfflineBanner';
import UploadPrescription from '../components/UploadPrescription';

const NAV = [
  { id: 'today', label: "Today's medicines" },
  { id: 'upload', label: 'Upload prescription' },
  { id: 'prescriptions', label: 'My prescriptions' },
  { id: 'settings', label: 'Language & reminders' },
  { id: 'emergency', label: 'Emergency help' },
];

const TIPS = {
  English: 'Take your medicines on time and drink plenty of clean water.',
  Hindi: 'दवा समय पर लें और खूब साफ़ पानी पिएं।',
  Gujarati: 'દવા સમયસર લો અને પુષ્કળ સ્વચ્છ પાણી પીઓ.',
};
const STATUS = { taken: 'Taken', due: 'Take now', missed: 'Missed', upcoming: 'Upcoming' };

const EMERGENCY = [
  { name: 'National emergency', number: '112' },
  { name: 'Ambulance', number: '108' },
  { name: 'Mother & child ambulance', number: '102' },
  { name: 'Child helpline', number: '1098' },
];

export default function PatientDashboard() {
  const { user, setUser } = useAuth();
  const lang = user.preferred_language;
  const [clock, setClock] = useState(() => ({ date: localDate(), now: localTime() }));
  const [speakAloud, setSpeakAloud] = useState(() => localStorage.getItem('sv:speakAloud') === '1');
  const [notifPerm, setNotifPerm] = useState(() => ('Notification' in window ? Notification.permission : 'unsupported'));
  const [msg, setMsg] = useState({ type: '', text: '' });

  // Refresh the schedule every minute so "due" and "missed" stay accurate
  useEffect(() => {
    const t = setInterval(() => setClock({ date: localDate(), now: localTime() }), 60000);
    return () => clearInterval(t);
  }, []);

  const doses = useCachedGet('/doses', { params: clock, cacheKey: 'doses' });
  const rxList = useCachedGet('/prescriptions');
  useReminders({ doses: doses.data?.doses, speakAloud, language: lang });

  const d = doses.data;
  const due = d?.doses.filter((x) => x.status === 'due') || [];
  const missed = d?.doses.filter((x) => x.status === 'missed') || [];

  async function mark(dose, taken) {
    try {
      await API.post('/doses/mark', {
        medication_id: dose.medication_id, date: dose.scheduled_date, time: dose.scheduled_time, taken,
      });
      doses.reload();
    } catch (err) {
      setMsg({ type: 'err', text: errorMessage(err) });
    }
  }

  async function changeLanguage(e) {
    try {
      const res = await API.patch('/users/me', { preferred_language: e.target.value });
      setUser(res.data);
      setMsg({ type: 'ok', text: 'Language updated.' });
    } catch (err) {
      setMsg({ type: 'err', text: errorMessage(err) });
    }
  }

  async function enableNotifications() {
    setNotifPerm(await Notification.requestPermission());
  }

  function toggleSpeak(e) {
    const on = e.target.checked;
    if (on && (!speechSupported() || !hasVoice(lang))) {
      setMsg({ type: 'err', text: `This phone has no ${lang} voice installed, so reminders cannot be spoken.` });
      return;
    }
    localStorage.setItem('sv:speakAloud', on ? '1' : '0');
    setSpeakAloud(on);
  }

  function listenTo(dose) {
    if (!speak(`${dose.medication_name}. ${dose.instructions || ''}`, lang)) {
      setMsg({ type: 'err', text: `This phone cannot read ${lang} aloud.` });
    }
  }

  return (
    <Layout nav={NAV} title="Patient Dashboard">
      <OfflineBanner offline={doses.offline || rxList.offline} savedAt={doses.savedAt || rxList.savedAt} />
      {msg.text && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      {due.length > 0 && (
        <div className="alert alert-due">
          <strong>💊 Time to take your medicine</strong>
          {due.map((x) => (
            <div className="row-between" key={`${x.medication_id}-${x.scheduled_time}`}>
              <span>{x.medication_name} {x.dose && `(${x.dose})`}</span>
              <button className="btn btn-primary" onClick={() => mark(x, true)}>I took it</button>
            </div>
          ))}
        </div>
      )}
      {missed.length > 0 && (
        <div className="alert alert-err">
          ⚠️ You missed {missed.length} dose{missed.length > 1 ? 's' : ''} today. If you are unsure what to do, ask your doctor or health worker.
        </div>
      )}

      <div className="grid stats">
        <StatCard label="Taken today" value={d ? `${d.taken}/${d.total}` : '…'} />
        <StatCard label="Missed" value={d ? d.missed : '…'} />
        <StatCard label="Prescriptions" value={rxList.data ? rxList.data.length : '…'} />
        <StatCard label="My language" value={lang} />
      </div>

      <div className="card tip">💡 {TIPS[lang] || TIPS.English}</div>

      <section id="today" className="card">
        <h2>Today&apos;s medicines</h2>
        {doses.error && <div className="alert alert-err">{doses.error}</div>}
        {d && d.doses.length === 0 && d.as_needed.length === 0 && (
          <p className="muted">No medicines scheduled today. Upload a prescription to get your schedule.</p>
        )}
        <ul className="list">
          {d?.doses.map((x) => (
            <li key={`${x.medication_id}-${x.scheduled_time}`} className={x.status === 'taken' ? 'done' : ''}>
              <div>
                <strong>{prettyTime(x.scheduled_time)}</strong> · {x.medication_name}
                {x.dose && <span className="muted"> · {x.dose}</span>}
                <div className="muted">{x.instructions}</div>
                <span className={`status st-${x.status}`}>{STATUS[x.status]}</span>
              </div>
              <div className="btn-row">
                <button className="btn btn-ghost" title="Listen" onClick={() => listenTo(x)}>🔊</button>
                {x.status === 'taken'
                  ? <button className="btn btn-ghost" onClick={() => mark(x, false)}>Undo</button>
                  : <button className="btn btn-primary" onClick={() => mark(x, true)}>Mark taken</button>}
              </div>
            </li>
          ))}
        </ul>
        {d?.as_needed.length > 0 && (
          <>
            <h3>Only when needed</h3>
            <ul className="list">
              {d.as_needed.map((x) => (
                <li key={x.medication_id}>
                  <div><strong>{x.medication_name}</strong>{x.dose && <span className="muted"> · {x.dose}</span>}
                    <div className="muted">{x.instructions}</div></div>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section id="upload" className="card">
        <h2>Upload a prescription</h2>
        <UploadPrescription defaultLanguage={lang} />
      </section>

      <section id="prescriptions" className="card">
        <h2>My prescriptions</h2>
        {rxList.data?.length === 0 && <p className="muted">Nothing here yet.</p>}
        <ul className="list">
          {rxList.data?.map((p) => (
            <li key={p.id}>
              <div>
                <strong>{p.title}</strong>
                <div className="muted">
                  {new Date(p.created_at).toLocaleDateString()} · {p.language}
                  {p.status === 'processed' && ` · ${p.medicine_count} medicine${p.medicine_count === 1 ? '' : 's'}`}
                </div>
                {p.status === 'failed' && <span className="status st-missed">Could not read</span>}
                {p.status === 'processed' && p.reviewed_at && <span className="status st-taken">Checked ✓</span>}
                {p.status === 'processed' && p.needs_review && <span className="status st-due">Needs checking</span>}
              </div>
              <Link className="btn btn-ghost" to={`/prescriptions/${p.id}`}>Open</Link>
            </li>
          ))}
        </ul>
      </section>

      <section id="settings" className="card">
        <h2>Language &amp; reminders</h2>
        <label className="inline">My language
          <select value={lang} onChange={changeLanguage}>
            <option>English</option><option>Hindi</option><option>Gujarati</option>
          </select>
        </label>
        <div className="settings-row">
          {notifPerm === 'granted' && <span className="status st-taken">Notifications on ✓</span>}
          {notifPerm === 'default' && <button className="btn btn-ghost" onClick={enableNotifications}>🔔 Turn on notifications</button>}
          {notifPerm === 'denied' && <span className="muted">Notifications are blocked in browser settings.</span>}
          <label className="check"><input type="checkbox" checked={speakAloud} onChange={toggleSpeak} /> Read reminders aloud</label>
        </div>
        <p className="muted">Reminders work while this app is open on your phone. Keep it open, or add it to your home screen.</p>
      </section>

      <section id="emergency" className="card">
        <h2>Emergency help</h2>
        <div className="grid emergency">
          {EMERGENCY.map((e) => (
            <a key={e.number} className="sos" href={`tel:${e.number}`}>
              <span>{e.name}</span><strong>{e.number}</strong>
            </a>
          ))}
        </div>
      </section>
    </Layout>
  );
}
