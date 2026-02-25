/**
 * Authentication Store
 *
 * Zustand store for managing authentication state.
 * Tokens are stored in httpOnly cookies (set by the server) and
 * are never accessible to JavaScript. Only user metadata and a
 * CSRF token are kept in memory / persisted.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User } from '@/types';
import { initializeAuthStore } from '@/lib/api-client';

/**
 * Auth store state interface
 */
interface AuthState {
  /** Current authenticated user */
  user: User | null;
  /** Whether user is authenticated */
  isAuthenticated: boolean;
  /** CSRF token issued by the server for state-changing requests */
  csrfToken: string | null;
}

/**
 * Auth store actions interface
 */
interface AuthActions {
  /** Set authentication data after login / register */
  setAuth: (user: User, csrfToken?: string) => void;
  /** Update the CSRF token (e.g. after refresh) */
  setCsrfToken: (csrfToken: string) => void;
  /** Clear all authentication data (logout) */
  clearAuth: () => void;
}

/**
 * Combined auth store type
 */
type AuthStore = AuthState & AuthActions;

/**
 * Initial state
 */
const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  csrfToken: null,
};

/**
 * Auth store with persistence
 *
 * Only the `user` object is persisted so the UI can render
 * immediately while the browser sends the httpOnly cookie
 * for actual authentication.
 */
export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      ...initialState,

      setAuth: (user: User, csrfToken?: string) => {
        set({
          user,
          isAuthenticated: true,
          ...(csrfToken != null ? { csrfToken } : {}),
        });
      },

      setCsrfToken: (csrfToken: string) => {
        set({ csrfToken });
      },

      clearAuth: () => {
        set(initialState);
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      // Persist only non-sensitive metadata — never tokens
      partialize: (state) => ({
        user: state.user,
      }),
      // Rehydrate isAuthenticated from persisted user
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isAuthenticated = !!state.user;
        }
      },
    }
  )
);

// Initialize the API client with the auth store reference
initializeAuthStore(useAuthStore);

/**
 * Selector hooks for common auth state
 */
export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useCsrfToken = () => useAuthStore((state) => state.csrfToken);

/**
 * Action hooks
 */
export const useAuthActions = () =>
  useAuthStore((state) => ({
    setAuth: state.setAuth,
    setCsrfToken: state.setCsrfToken,
    clearAuth: state.clearAuth,
  }));

export default useAuthStore;
