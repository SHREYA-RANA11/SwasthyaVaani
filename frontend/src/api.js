import axios from 'axios';

// Set VITE_API_URL in frontend/.env to change this (e.g. for deployment)
const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
});

API.interceptors.request.use((req) => {
  const token = localStorage.getItem('token');
  if (token) {
    req.headers.Authorization = `Bearer ${token}`;
  }
  return req;
});

// Turn any backend/network error into a readable message
export function errorMessage(err) {
  const data = err?.response?.data;
  if (!err?.response) return 'Cannot reach the server. Is the backend running?';
  if (Array.isArray(data?.detail)) {
    const d = data.detail[0];
    return `${d.loc?.[d.loc.length - 1] ?? 'input'}: ${d.msg}`;
  }
  return data?.detail || 'Something went wrong. Please try again.';
}

export default API;
