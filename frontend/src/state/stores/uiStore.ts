/**
 * UI Store
 * 
 * Zustand store for managing UI state including sidebar state
 * and theme preferences. Persisted to localStorage.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

/**
 * Theme type
 */
export type Theme = 'light' | 'dark';

/**
 * Notification preferences
 */
export interface NotificationPreferences {
  emailAlerts: boolean;
  pushNotifications: boolean;
  weeklyDigest: boolean;
}

/**
 * UI store state interface
 */
interface UIState {
  /** Whether sidebar is open (mobile) */
  sidebarOpen: boolean;
  /** Whether sidebar is collapsed (desktop) */
  sidebarCollapsed: boolean;
  /** Current theme */
  theme: Theme;
  /** Notification preferences */
  notifications: NotificationPreferences;
}

/**
 * UI store actions interface
 */
interface UIActions {
  /** Toggle sidebar open/closed */
  toggleSidebar: () => void;
  /** Set sidebar open state explicitly */
  setSidebarOpen: (open: boolean) => void;
  /** Toggle sidebar collapsed state */
  collapseSidebar: () => void;
  /** Set sidebar collapsed state explicitly */
  setSidebarCollapsed: (collapsed: boolean) => void;
  /** Toggle theme between light and dark */
  toggleTheme: () => void;
  /** Set theme explicitly */
  setTheme: (theme: Theme) => void;
  /** Toggle a notification preference */
  toggleNotification: (key: keyof NotificationPreferences) => void;
  /** Set notification preferences explicitly */
  setNotifications: (prefs: Partial<NotificationPreferences>) => void;
}

/**
 * Combined UI store type
 */
type UIStore = UIState & UIActions;

/**
 * Get system preference for color scheme
 */
function getSystemTheme(): Theme {
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }
  return 'light';
}

/**
 * Initial state
 */
const initialState: UIState = {
  sidebarOpen: false,
  sidebarCollapsed: false,
  theme: 'light', // Will be overridden by persist or system preference
  notifications: {
    emailAlerts: true,
    pushNotifications: true,
    weeklyDigest: false,
  },
};

/**
 * UI store with persistence
 */
export const useUIStore = create<UIStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }));
      },

      setSidebarOpen: (open: boolean) => {
        set({ sidebarOpen: open });
      },

      collapseSidebar: () => {
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }));
      },

      setSidebarCollapsed: (collapsed: boolean) => {
        set({ sidebarCollapsed: collapsed });
      },

      toggleTheme: () => {
        const newTheme = get().theme === 'light' ? 'dark' : 'light';
        set({ theme: newTheme });
        applyTheme(newTheme);
      },

      setTheme: (theme: Theme) => {
        set({ theme });
        applyTheme(theme);
      },

      toggleNotification: (key: keyof NotificationPreferences) => {
        set((state) => ({
          notifications: {
            ...state.notifications,
            [key]: !state.notifications[key],
          },
        }));
      },

      setNotifications: (prefs: Partial<NotificationPreferences>) => {
        set((state) => ({
          notifications: { ...state.notifications, ...prefs },
        }));
      },
    }),
    {
      name: 'ui-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        notifications: state.notifications,
      }),
      // Apply theme on rehydration
      onRehydrateStorage: () => (state) => {
        if (state) {
          // If no stored theme, use system preference
          if (!state.theme) {
            state.theme = getSystemTheme();
          }
          applyTheme(state.theme);
        }
      },
    }
  )
);

/**
 * Apply theme to document
 */
function applyTheme(theme: Theme): void {
  if (typeof document !== 'undefined') {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }
}

/**
 * Initialize theme on first load
 */
if (typeof window !== 'undefined') {
  // Check if already rehydrated
  const stored = localStorage.getItem('ui-storage');
  if (!stored) {
    // Apply system preference if no stored preference
    applyTheme(getSystemTheme());
  }
}

/**
 * Selector hooks for common UI state
 */
export const useTheme = () => useUIStore((state) => state.theme);
export const useSidebarOpen = () => useUIStore((state) => state.sidebarOpen);
export const useSidebarCollapsed = () => useUIStore((state) => state.sidebarCollapsed);
export const useNotifications = () => useUIStore((state) => state.notifications);

/**
 * Action hooks
 *
 * Note: We use separate selectors for each action to avoid returning
 * a new object on every render, which can cause React's
 * useSyncExternalStore to warn about unstable snapshots and can
 * contribute to update loops in StrictMode.
 */
export const useUIActions = () => {
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);
  const setSidebarOpen = useUIStore((state) => state.setSidebarOpen);
  const collapseSidebar = useUIStore((state) => state.collapseSidebar);
  const setSidebarCollapsed = useUIStore((state) => state.setSidebarCollapsed);
  const toggleTheme = useUIStore((state) => state.toggleTheme);
  const setTheme = useUIStore((state) => state.setTheme);
  const toggleNotification = useUIStore((state) => state.toggleNotification);
  const setNotifications = useUIStore((state) => state.setNotifications);

  return {
    toggleSidebar,
    setSidebarOpen,
    collapseSidebar,
    setSidebarCollapsed,
    toggleTheme,
    setTheme,
    toggleNotification,
    setNotifications,
  };
};

/**
 * Combined sidebar state hook
 */
export const useSidebarState = () =>
  useUIStore((state) => ({
    isOpen: state.sidebarOpen,
    isCollapsed: state.sidebarCollapsed,
    toggle: state.toggleSidebar,
    setOpen: state.setSidebarOpen,
    toggleCollapse: state.collapseSidebar,
  }));

export default useUIStore;
