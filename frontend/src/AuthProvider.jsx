import { useCallback, useEffect, useMemo, useState } from 'react';
import API from './api';
import { AuthContext } from './auth-context';

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(localStorage.getItem('token')));

  // Restore the session when the page is refreshed.
  // Offline? Keep the patient signed in using the copy saved on the phone.
  useEffect(() => {
    if (!localStorage.getItem('token')) return;
    API.get('/auth/me')
      .then((res) => {
        localStorage.setItem('sv:user', JSON.stringify(res.data));
        setUser(res.data);
      })
      .catch((err) => {
        if (!err.response) {
          try {
            const saved = JSON.parse(localStorage.getItem('sv:user'));
            if (saved) return setUser(saved);
          } catch { /* fall through */ }
        }
        localStorage.removeItem('token'); // token rejected or nothing saved
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await API.post('/auth/login', { email, password });
    localStorage.setItem('token', res.data.access_token);
    const me = await API.get('/auth/me');
    localStorage.setItem('sv:user', JSON.stringify(me.data));
    setUser(me.data);
    return me.data;
  }, []);

  const register = useCallback(async (kind, payload) => {
    await API.post(`/auth/register/${kind}`, payload);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('sv:user');
    setUser(null);
  }, []);

  const updateUser = useCallback((u) => {
    localStorage.setItem('sv:user', JSON.stringify(u));
    setUser(u);
  }, []);

  const value = useMemo(
    () => ({ user, setUser: updateUser, loading, login, register, logout }),
    [user, updateUser, loading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
