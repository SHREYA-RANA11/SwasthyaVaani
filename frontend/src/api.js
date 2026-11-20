import axios from 'axios';

// Backend API configuration
const API = axios.create({
  baseURL:
    import.meta.env.VITE_API_URL ||
    'http://127.0.0.1:8000',
});

// Automatically attach JWT token to requests
API.interceptors.request.use((req) => {
  const token = localStorage.getItem('token');

  if (token) {
    req.headers.Authorization = `Bearer ${token}`;
  }

  return req;
});

// Convert backend/network errors into readable messages
export function errorMessage(err) {
  const data = err?.response?.data;

  if (!err?.response) {
    return 'Cannot reach the server. Is the backend running?';
  }

  if (Array.isArray(data?.detail)) {
    const d = data.detail[0];

    return `${d.loc?.[d.loc.length - 1] ?? 'input'}: ${d.msg}`;
  }

  return data?.detail || 'Something went wrong. Please try again.';
}

// Get the logged-in user's profile
export async function getMyProfile() {
  const response = await API.get('/auth/me');
  return response.data;
}

// Update the logged-in user's profile
export async function updateMyProfile(profileData) {
  const response = await API.put('/auth/me', profileData);
  return response.data;
}

export default API;