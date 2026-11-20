import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMyProfile, updateMyProfile, errorMessage } from '../api';
// import { useAuth } from '../useAuth';

export default function ProfilePage() {
//   const { user } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({
    full_name: '',
    phone: '',
    date_of_birth: '',
    gender: '',
    address: '',
    native_language: '',
    preferred_language: '',
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  // Load patient profile
  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    setLoading(true);
    setError('');

    try {
      const data = await getMyProfile();

      setProfile(data);

      setForm({
        full_name: data.full_name || '',
        phone: data.phone || '',
        date_of_birth: data.date_of_birth || '',
        gender: data.gender || '',
        address: data.address || '',
        native_language: data.native_language || 'English',
        preferred_language: data.preferred_language || 'English',
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  // Handle form changes
  function handleChange(e) {
    const { name, value } = e.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  // Save profile changes
  async function handleSubmit(e) {
    e.preventDefault();

    setError('');
    setNotice('');
    setSaving(true);

    try {
      const updated = await updateMyProfile({
        full_name: form.full_name.trim(),
        phone: form.phone.trim() || null,
        date_of_birth: form.date_of_birth || null,
        gender: form.gender || null,
        address: form.address.trim() || null,
        native_language: form.native_language,
        preferred_language: form.preferred_language,
      });

      setProfile(updated);
      setEditing(false);
      setNotice('Your profile has been updated successfully.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  // Cancel editing
  function cancelEditing() {
    if (!profile) return;

    setForm({
      full_name: profile.full_name || '',
      phone: profile.phone || '',
      date_of_birth: profile.date_of_birth || '',
      gender: profile.gender || '',
      address: profile.address || '',
      native_language: profile.native_language || 'English',
      preferred_language: profile.preferred_language || 'English',
    });

    setEditing(false);
    setError('');
    setNotice('');
  }

  if (loading) {
    return <div className="center-screen">Loading profile…</div>;
  }

  if (!profile) {
    return (
      <div className="profile-page">
        <div className="profile-card">
          <h2>Unable to load profile</h2>
          <p>{error || 'Please try again.'}</p>
          <button className="profile-btn" onClick={loadProfile}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="profile-container">

        {/* Header */}
        <div className="profile-header">
          <div>
            <p className="profile-eyebrow">ACCOUNT SETTINGS</p>
            <h1>My Profile</h1>
            <p>Manage your personal information and language preferences.</p>
          </div>

          <button
            className="profile-back-btn"
            onClick={() => navigate('/patient')}
          >
            ← Back to Dashboard
          </button>
        </div>

        {notice && (
          <div className="profile-success">
            ✓ {notice}
          </div>
        )}

        {error && (
          <div className="profile-error">
            {error}
          </div>
        )}

        {/* Profile summary */}
        <div className="profile-card profile-summary">
          <div className="profile-avatar">
            {(profile.full_name || 'P').charAt(0).toUpperCase()}
          </div>

          <div className="profile-summary-info">
            <h2>{profile.full_name}</h2>
            <p>{profile.email}</p>
            <span className="profile-role">
              {profile.role === 'patient' ? 'Patient Account' : profile.role}
            </span>
          </div>

          {!editing && (
            <button
              className="profile-btn"
              onClick={() => {
                setEditing(true);
                setNotice('');
                setError('');
              }}
            >
              ✎ Edit Profile
            </button>
          )}
        </div>

        {/* Profile form */}
        <form className="profile-card" onSubmit={handleSubmit}>
          <div className="profile-section-heading">
            <div>
              <h2>Personal Information</h2>
              <p>Your basic account and contact details.</p>
            </div>
          </div>

          <div className="profile-grid">

            <label>
              Full name
              <input
                name="full_name"
                value={form.full_name}
                onChange={handleChange}
                disabled={!editing}
                required
                minLength={2}
                maxLength={100}
              />
            </label>

            <label>
              Email address
              <input
                type="email"
                value={profile.email || ''}
                disabled
              />
            </label>

            <label>
              Phone number
              <input
                name="phone"
                value={form.phone}
                onChange={handleChange}
                disabled={!editing}
                maxLength={20}
              />
            </label>

            <label>
              Date of birth
              <input
                type="date"
                name="date_of_birth"
                value={form.date_of_birth}
                onChange={handleChange}
                disabled={!editing}
              />
            </label>

            <label>
              Gender
              <select
                name="gender"
                value={form.gender}
                onChange={handleChange}
                disabled={!editing}
              >
                <option value="">Select gender</option>
                <option value="Female">Female</option>
                <option value="Male">Male</option>
                <option value="Other">Other</option>
                <option value="Prefer not to say">Prefer not to say</option>
              </select>
            </label>

            <label className="profile-full-width">
              Address
              <textarea
                name="address"
                value={form.address}
                onChange={handleChange}
                disabled={!editing}
                rows={3}
                maxLength={500}
                placeholder="Enter your address"
              />
            </label>

          </div>

          {/* Language preferences */}
          <div className="profile-section-heading language-heading">
            <div>
              <h2>Language Preferences</h2>
              <p>Choose the languages used for your healthcare guidance.</p>
            </div>
          </div>

          <div className="profile-grid">

            <label>
              Native language
              <select
                name="native_language"
                value={form.native_language}
                onChange={handleChange}
                disabled={!editing}
                required
              >
                <option value="Gujarati">Gujarati</option>
                <option value="Hindi">Hindi</option>
                <option value="English">English</option>
              </select>
            </label>

            <label>
              Preferred language for medical explanations
              <select
                name="preferred_language"
                value={form.preferred_language}
                onChange={handleChange}
                disabled={!editing}
                required
              >
                <option value="Gujarati">Gujarati</option>
                <option value="Hindi">Hindi</option>
                <option value="English">English</option>
              </select>
            </label>

          </div>

          {/* Account information */}
          <div className="profile-account-info">
            <span>Account ID: #{profile.id}</span>
            <span>Account status: {profile.is_active ? 'Active' : 'Inactive'}</span>
          </div>

          {/* Action buttons */}
          {editing && (
            <div className="profile-actions">
              <button
                type="button"
                className="profile-cancel-btn"
                onClick={cancelEditing}
                disabled={saving}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="profile-btn"
                disabled={saving}
              >
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
            </div>
          )}

        </form>

      </div>
    </div>
  );
}