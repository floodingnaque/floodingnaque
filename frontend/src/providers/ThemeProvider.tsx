/* eslint-disable react-refresh/only-export-components */
/**
 * Theme Provider
 *
 * Provides theme context for the application, managing light/dark mode
 * with system preference detection and localStorage persistence.
 */

import {
  createContext,
  useContext,
  useEffect,
  type ReactNode,
} from 'react';
import { useUIStore, type Theme } from '@/state/stores/uiStore';

/**
 * Theme context value interface
 */
interface ThemeContextValue {
  /** Current theme */
  theme: Theme;
  /** Set the theme */
  setTheme: (theme: Theme) => void;
  /** Toggle between light and dark */
  toggleTheme: () => void;
}

/**
 * Theme context
 */
const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

/**
 * Props for ThemeProvider
 */
interface ThemeProviderProps {
  children: ReactNode;
  /** Default theme if none stored */
  defaultTheme?: Theme;
  /** Storage key for theme persistence */
  storageKey?: string;
}

/**
 * ThemeProvider component
 *
 * Manages theme state and applies theme class to document root.
 * Syncs with system preference and persists to localStorage.
 */
export function ThemeProvider({
  children,
  defaultTheme = 'light',
}: ThemeProviderProps) {
  const theme = useUIStore((state) => state.theme);
  const setTheme = useUIStore((state) => state.setTheme);
  const toggleTheme = useUIStore((state) => state.toggleTheme);

  // Apply theme to document on mount and theme change
  useEffect(() => {
    const root = document.documentElement;

    // Remove both classes first
    root.classList.remove('light', 'dark');

    // Determine effective theme
    let effectiveTheme = theme;

    // If no theme is set, check localStorage or system preference
    if (!effectiveTheme) {
      const stored = localStorage.getItem('ui-storage');
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          effectiveTheme = parsed.state?.theme || defaultTheme;
        } catch {
          effectiveTheme = defaultTheme;
        }
      } else {
        // Use system preference
        effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
          ? 'dark'
          : 'light';
      }
      // Set the theme in store
      setTheme(effectiveTheme);
    }

    // Apply theme class
    root.classList.add(effectiveTheme);

    // Update color-scheme CSS property for native elements
    root.style.colorScheme = effectiveTheme;
  }, [theme, defaultTheme, setTheme]);

  // Listen for system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      // Only auto-switch if user hasn't explicitly set a preference
      const stored = localStorage.getItem('ui-storage');
      if (!stored) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [setTheme]);

  const value: ThemeContextValue = {
    theme,
    setTheme,
    toggleTheme,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Hook to access theme context
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);

  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }

  return context;
}

export default ThemeProvider;
