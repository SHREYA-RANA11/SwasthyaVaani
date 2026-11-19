import { useCallback, useEffect, useState } from 'react';
import { applyTheme, saveTheme, savedTheme, systemTheme } from './theme';

export function useTheme() {
  const [theme, setTheme] = useState(() => savedTheme() || systemTheme());

  useEffect(() => { applyTheme(theme); }, [theme]);

  const toggle = useCallback(() => {
    const next = theme === 'dark' ? 'light' : 'dark';
    saveTheme(next);
    setTheme(next);
  }, [theme]);

  return { theme, toggle };
}
