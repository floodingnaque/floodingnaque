/**
 * Authentication Store
 *
 * Zustand store for managing authentication state.
 * Access and refresh tokens are kept in memory (never persisted).
 * Only user metadata is persisted to localStorage.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { useMemo } from 'react';
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
  /** Whether Zustand has finished rehydrating persisted state */
  hasHydrated: boolean;
  /** CSRF token issued by the server for state-changing requests */
  csrfToken: string | null;
  /** JWT access token (in-memory only, never persisted) */
  accessToken: string | null;
  /** JWT refresh token (in-memory only, never persisted) */
  refreshToken: string | null;
}

/**
 * Auth store actions interface
 */
interface AuthActions {
  /** Set authentication data after login / register */
  setAuth: (user: User, csrfToken?: string, accessToken?: string, refreshToken?: string) => void;
  /** Update the CSRF token (e.g. after refresh) */
  setCsrfToken: (csrfToken: string) => void;
  /** Update the access token (e.g. after refresh) */
  setAccessToken: (accessToken: string) => void;
  /** Clear all authentication data (logout) */
  clearAuth: () => void;
  /** Mark Zustand rehydration as complete */
  setHasHydrated: (v: boolean) => void;
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
  hasHydrated: false,
  csrfToken: null,
  accessToken: null,
  refreshToken: null,
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

      setAuth: (user: User, csrfToken?: string, accessToken?: string, refreshToken?: string) => {
        set({
          user,
          isAuthenticated: true,
          ...(csrfToken != null ? { csrfToken } : {}),
          ...(accessToken != null ? { accessToken } : {}),
          ...(refreshToken != null ? { refreshToken } : {}),
        });
      },

      setCsrfToken: (csrfToken: string) => {
        set({ csrfToken });
      },

      setAccessToken: (accessToken: string) => {
        set({ accessToken });
      },

      clearAuth: () => {
        set({ ...initialState, hasHydrated: true });
      },

      setHasHydrated: (v: boolean) => {
        set({ hasHydrated: v });
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      // Persist only non-sensitive metadata - never tokens
      partialize: (state) => ({
        user: state.user,
      }),
      // After rehydration: persisted user is available but tokens are NOT
      // (they live in memory only).  Mark isAuthenticated = false so the
      // app can attempt a silent token refresh rather than flash-then-logout.
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Tokens were not persisted, so we cannot consider the user
          // truly authenticated until a refresh succeeds.
          state.isAuthenticated = false;
          state.hasHydrated = true;
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
export const useHasHydrated = () => useAuthStore((state) => state.hasHydrated);
export const useCsrfToken = () => useAuthStore((state) => state.csrfToken);

/**
 * Action hooks - each selector returns a stable reference to avoid
 * defeating React.memo / shallow-equality checks.
 */
export const useSetAuth = () => useAuthStore((state) => state.setAuth);
export const useSetCsrfToken = () => useAuthStore((state) => state.setCsrfToken);
export const useClearAuth = () => useAuthStore((state) => state.clearAuth);

/**
 * Combined actions object - kept for backward compatibility but
 * consumers that only need one action should prefer the individual hooks
 * above to avoid creating a new object on every render.
 */
export const useAuthActions = () => {
  const setAuth = useSetAuth();
  const setCsrfToken = useSetCsrfToken();
  const clearAuth = useClearAuth();
  return useMemo(() => ({ setAuth, setCsrfToken, clearAuth }), [setAuth, setCsrfToken, clearAuth]);
};

export default useAuthStore;
