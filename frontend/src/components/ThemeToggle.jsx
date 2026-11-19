import { useTheme } from '../useTheme';

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const dark = theme === 'dark';
  const label = dark ? 'Switch to light theme' : 'Switch to dark theme';
  return (
    <button type="button" className="theme-toggle" onClick={toggle} aria-label={label} title={label}>
      <span aria-hidden="true">{dark ? '☀️' : '🌙'}</span>
    </button>
  );
}
