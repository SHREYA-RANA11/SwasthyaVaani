// Light / dark theme: remembered on this device. Until the user chooses, follow the device.
const KEY = 'sv:theme';

export function systemTheme() {
  const m = window.matchMedia?.('(prefers-color-scheme: dark)');
  return m?.matches ? 'dark' : 'light';
}

export function savedTheme() {
  try {
    const t = localStorage.getItem(KEY);
    return t === 'dark' || t === 'light' ? t : null;
  } catch {
    return null;
  }
}

export function saveTheme(theme) {
  try { localStorage.setItem(KEY, theme); } catch { /* private mode: just do not remember */ }
}

export function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
}
