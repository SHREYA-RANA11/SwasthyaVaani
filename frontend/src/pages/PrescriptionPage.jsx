import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import API, { errorMessage } from '../api';
import { useAuth } from '../useAuth';
import { useCachedGet } from '../useCachedGet';
import { hasVoice, prescriptionScript, speak, speechSupported, stopSpeaking } from '../speech';
import { prettyTime } from '../time';
import Layout from '../components/Layout';
import OfflineBanner from '../components/OfflineBanner';

const FOOD = {
  before_food: { English: 'Before food', Hindi: 'खाने से पहले', Gujarati: 'જમતા પહેલાં' },
  after_food: { English: 'After food', Hindi: 'खाने के बाद', Gujarati: 'જમ્યા પછી' },
  with_food: { English: 'With food', Hindi: 'खाने के साथ', Gujarati: 'જમતી વખતે' },
};
const LABEL = {
  medicines: { English: 'Your medicines', Hindi: 'आपकी दवाइयाँ', Gujarati: 'તમારી દવાઓ' },
  times: { English: 'Times', Hindi: 'समय', Gujarati: 'સમય' },
  days: { English: 'days', Hindi: 'दिन', Gujarati: 'દિવસ' },
  careful: { English: 'Important', Hindi: 'ज़रूरी बातें', Gujarati: 'મહત્વની વાતો' },
  asNeeded: { English: 'Only when needed', Hindi: 'सिर्फ़ ज़रूरत पड़ने पर', Gujarati: 'ફક્ત જરૂર પડે ત્યારે' },
};

export default function PrescriptionPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: rx, error, loading, offline, savedAt, reload } = useCachedGet(`/prescriptions/${id}`);
  const [image, setImage] = useState(null);
  const [speaking, setSpeaking] = useState(false);
  const [msg, setMsg] = useState({ type: '', text: '' });
  const [busy, setBusy] = useState(false);

  const isPatient = user.role === 'patient';
  const home = isPatient ? '/patient' : user.role === 'admin' ? '/admin' : '/worker';
  const nav = [{ to: home, label: '← Back to dashboard' }];

  // Load the original photo (needs the login token, so it is fetched, not linked)
  useEffect(() => {
    let url;
    let alive = true;
    API.get(`/prescriptions/${id}/file`, { responseType: 'blob' })
      .then((r) => { if (alive) { url = URL.createObjectURL(r.data); setImage(url); } })
      .catch(() => {});
    return () => { alive = false; if (url) URL.revokeObjectURL(url); stopSpeaking(); };
  }, [id]);

  if (loading) return <Layout nav={nav} title="Prescription"><p className="muted">Loading…</p></Layout>;
  if (error) return <Layout nav={nav} title="Prescription"><div className="alert alert-err">{error}</div></Layout>;

  const lang = rx.language;

  function listen() {
    if (speaking) { stopSpeaking(); setSpeaking(false); return; }
    if (!speechSupported()) return setMsg({ type: 'err', text: 'This browser cannot read aloud. Try Chrome.' });
    if (!hasVoice(lang)) {
      return setMsg({ type: 'err', text: `This phone has no ${lang} voice installed. Install it in your phone's Text-to-speech settings, or choose Hindi or English.` });
    }
    setMsg({ type: '', text: '' });
    setSpeaking(speak(prescriptionScript(rx), lang, () => setSpeaking(false)));
  }

  async function act(fn, okText) {
    setBusy(true);
    setMsg({ type: '', text: '' });
    try {
      await fn();
      if (okText) setMsg({ type: 'ok', text: okText });
      reload();
    } catch (err) {
      setMsg({ type: 'err', text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  const reanalyze = (language) => act(() => API.post(`/prescriptions/${id}/analyze`, { language }), '');
  const verify = () => act(() => API.post(`/prescriptions/${id}/review`), 'Marked as verified.');
  async function remove() {
    if (!window.confirm('Delete this prescription and its medicine schedule?')) return;
    try {
      await API.delete(`/prescriptions/${id}`);
      navigate(home, { replace: true });
    } catch (err) {
      setMsg({ type: 'err', text: errorMessage(err) });
    }
  }

  return (
    <Layout nav={nav} title={rx.title}>
      <OfflineBanner offline={offline} savedAt={savedAt} />
      {msg.text && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      {rx.ai_provider === 'mock' && (
        <div className="alert alert-warn">
          🧪 Demo mode: no AI key is set on the server, so this is <strong>sample text, not your photo</strong>.
        </div>
      )}
      {rx.status === 'processed' && rx.reviewed_at && (
        <div className="alert alert-ok">✅ Checked by {rx.reviewed_by_name || 'a healthcare worker'}.</div>
      )}
      {rx.status === 'processed' && rx.needs_review && (
        <div className="alert alert-warn">
          ⚠️ The photo was hard to read, so this explanation may have mistakes. Please show the original to your doctor or health worker before taking medicine.
        </div>
      )}

      <div className="grid two">
        <div className="card">
          <h2>Original prescription</h2>
          {image ? <img className="rx-image" src={image} alt="Original prescription" />
            : <p className="muted">{offline ? 'Photo is not saved offline.' : 'Photo not available.'}</p>}
          <p className="muted">{[rx.doctor_name, rx.diagnosis].filter(Boolean).join(' · ')}</p>
        </div>

        <div className="card">
          <div className="row-between">
            <h2>In {lang}</h2>
            {rx.status === 'processed' && (
              <button className="btn btn-primary" onClick={listen}>{speaking ? '⏹ Stop' : '🔊 Listen'}</button>
            )}
          </div>

          {rx.status === 'failed' && (
            <div className="alert alert-err">
              {rx.error_message}
              {isPatient && (
                <div><button className="btn btn-ghost" disabled={busy || offline} onClick={() => reanalyze(lang)}>
                  {busy ? 'Trying…' : 'Try again'}
                </button></div>
              )}
            </div>
          )}

          {rx.status === 'processed' && (
            <>
              <p className="summary">{rx.summary}</p>
              {rx.warnings.length > 0 && (
                <>
                  <h3>{LABEL.careful[lang]}</h3>
                  <ul className="bullets">{rx.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
                </>
              )}
              {rx.follow_up && <p>📅 {rx.follow_up}</p>}
            </>
          )}

          {isPatient && rx.status !== 'failed' && (
            <label className="inline">Explain in a different language
              <select value={lang} disabled={busy || offline} onChange={(e) => reanalyze(e.target.value)}>
                <option>English</option><option>Hindi</option><option>Gujarati</option>
              </select>
            </label>
          )}
        </div>
      </div>

      {rx.status === 'processed' && (
        <section className="card">
          <h2>{LABEL.medicines[lang]}</h2>
          <div className="meds">
            {rx.medications.map((m) => (
              <div className="med" key={m.id}>
                <div className="row-between">
                  <strong>{m.name}</strong>
                  {m.dose && <span className="badge">{m.dose}</span>}
                </div>
                <p>{m.instructions_simple}</p>
                <div className="chips">
                  {m.times.length > 0
                    ? m.times.map((t) => <span className="chip" key={t}>⏰ {prettyTime(t)}</span>)
                    : <span className="chip">{LABEL.asNeeded[lang]}</span>}
                  {FOOD[m.food] && <span className="chip">🍽 {FOOD[m.food][lang]}</span>}
                  {m.duration_days && <span className="chip">{m.duration_days} {LABEL.days[lang]}</span>}
                </div>
                {m.instructions_original && <p className="muted">Original: {m.instructions_original}</p>}
              </div>
            ))}
            {rx.medications.length === 0 && <p className="muted">No medicines were found on this document.</p>}
          </div>
          <details>
            <summary>Text read from the original prescription</summary>
            <pre className="raw">{rx.extracted_text || 'Nothing was read.'}</pre>
          </details>
        </section>
      )}

      <p className="disclaimer">ℹ️ {rx.disclaimer}</p>

      <div className="actions">
        {!isPatient && rx.status === 'processed' && !rx.reviewed_at && (
          <button className="btn btn-primary" disabled={busy} onClick={verify}>
            ✅ I checked this against the original — mark as verified
          </button>
        )}
        {isPatient && <button className="btn btn-ghost danger" onClick={remove}>Delete prescription</button>}
      </div>
    </Layout>
  );
}
