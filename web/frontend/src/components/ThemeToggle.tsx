'use client';

import { useEffect, useState } from 'react';

/**
 * ThemeToggle — no longer renders a floating button.
 * Keeps the theme detection + localStorage logic so it applies on mount.
 * Actual toggle UI lives in the header/settings menu.
 */
export default function ThemeToggle() {
  useEffect(() => {
    const saved = localStorage.getItem('theme');
    const isDark = saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('dark', isDark);
  }, []);

  return null;
}

/**
 * useTheme — hook for any component that needs dark state + toggle.
 */
export function useTheme() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('theme');
    const isDark = saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches);
    setDark(isDark);
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };

  return { dark, toggle };
}
