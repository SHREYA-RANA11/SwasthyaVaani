import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../useAuth';
import { errorMessage } from '../api';
import { HOME_BY_ROLE } from '../roles';
import ThemeToggle from '../components/ThemeToggle';

export default function AuthPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', password: '' });
  const [kind, setKind] = useState('patient');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError('');
    setNotice('');
    setBusy(true);
    try {
      if (mode === 'register') {
        await register(kind, {
          full_name: form.full_name,
          email: form.email,
          phone: form.phone || null,
          password: form.password,
        });
        setNotice('Account created. Please log in.');
        setMode('login');
        setForm({ ...form, password: '' });
      } else {
        const me = await login(form.email, form.password);
        navigate(HOME_BY_ROLE[me.role], { replace: true });
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-theme"><ThemeToggle /></div>
      <div className="auth-hero">
        <div className="hero-brand"><span className="brand-mark">+</span> SwasthyaVaani</div>
        <h1>Understand your medicines in your own language</h1>
        <p>Take a photo of your prescription. We explain it in simple Hindi, Gujarati or English, and read it aloud.</p>
        <ul className="hero-points">
          <li><span className="ico">📷</span><div><strong>Photo to explanation</strong><small>No typing, no medical jargon</small></div></li>
          <li><span className="ico">🔊</span><div><strong>Voice guidance</strong><small>For patients who cannot read</small></div></li>
          <li><span className="ico">⏰</span><div><strong>Medicine reminders</strong><small>Never miss a dose, works offline</small></div></li>
        </ul>
      </div>

      <form className="card auth-card" onSubmit={submit}>
        <h2>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2>

        {notice && <div className="alert alert-ok">{notice}</div>}
        {error && <div className="alert alert-err">{error}</div>}

        {mode === 'register' && (
          <>
            <label>I am a
              <select value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="patient">Patient</option>
                <option value="healthcare-worker">Healthcare worker</option>
              </select>
            </label>
            <label>Full name
              <input required minLength={2} value={form.full_name} onChange={set('full_name')} />
            </label>
            <label>Phone (optional)
              <input value={form.phone} onChange={set('phone')} />
            </label>
          </>
        )}

        <label>Email
          <input type="email" required value={form.email} onChange={set('email')} />
        </label>
        <label>Password
          <input type="password" required minLength={mode === 'register' ? 8 : 1}
                 value={form.password} onChange={set('password')} />
        </label>

        <button className="btn btn-primary" disabled={busy}>
          {busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Register'}
        </button>

        <p className="switch">
          {mode === 'login' ? 'New here? ' : 'Already registered? '}
          <button type="button" className="link"
                  onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); setNotice(''); }}>
            {mode === 'login' ? 'Create an account' : 'Log in'}
          </button>
        </p>
      </form>
    </div>
  );
}
