import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import API, { errorMessage } from '../api';
import { compressImage } from '../compressImage';

export default function UploadPrescription({ defaultLanguage }) {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [language, setLanguage] = useState(defaultLanguage);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function pick(e) {
    setError('');
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.type.startsWith('image/')) {
      setError('Please choose a photo (JPG or PNG) of the prescription.');
      return;
    }
    setFile(f);
  }

  async function submit(e) {
    e.preventDefault();
    if (!file) return setError('Please choose or take a photo first.');
    setBusy(true);
    setError('');
    try {
      const small = await compressImage(file);
      const fd = new FormData();
      fd.append('file', small);
      fd.append('language', language);
      if (title.trim()) fd.append('title', title.trim());
      const res = await API.post('/prescriptions', fd, { timeout: 150000 });
      navigate(`/prescriptions/${res.data.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="upload">
      <label className="dropzone">
        {preview ? <img src={preview} alt="Selected prescription" /> : (
          <span>📷 Tap to take a photo or choose a picture of your prescription</span>
        )}
        <input type="file" accept="image/*" onChange={pick} disabled={busy} hidden />
      </label>

      <div className="upload-fields">
        <label>Name (optional)
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Fever medicine" disabled={busy} />
        </label>
        <label>Explain it in
          <select value={language} onChange={(e) => setLanguage(e.target.value)} disabled={busy}>
            <option>English</option>
            <option>Hindi</option>
            <option>Gujarati</option>
          </select>
        </label>
        {error && <div className="alert alert-err">{error}</div>}
        {busy && <div className="alert alert-ok">⏳ Reading your prescription… this can take up to a minute. Please keep this page open.</div>}
        <button className="btn btn-primary" disabled={busy || !file}>
          {busy ? 'Please wait…' : 'Read my prescription'}
        </button>
      </div>
    </form>
  );
}
