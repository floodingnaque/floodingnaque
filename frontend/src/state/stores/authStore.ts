/**
 * Authentication Store
 *
 * Zustand store for managing authentication state including
 * user data, tokens, and authentication status.
 * Persisted to localStorage.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User, AuthTokens } from '@/types';
import { initializeAuthStore } from '@/lib/api-client';

/**
 * Auth store state interface
 */
interface AuthState {
  /** Current authenticated user */
  user: User | null;
  /** JWT access token */
  accessToken: string | null;
  /** JWT refresh token */
  refreshToken: string | null;
  /** Whether user is authenticated (derived from accessToken) */
  isAuthenticated: boolean;
}

/**
 * Auth store actions interface
 */
interface AuthActions {
  /** Set authentication data (user and tokens) */
  setAuth: (user: User, tokens: AuthTokens) => void;
  /** Update tokens only */
  setTokens: (tokens: AuthTokens) => void;
  /** Clear all authentication data */
  clearAuth: () => void;
  /** Get the current access token */
  getAccessToken: () => string | null;
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
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
};

/**
 * Auth store with persistence
 */
export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setAuth: (user: User, tokens: AuthTokens) => {
        set({
          user,
          accessToken: tokens.accessToken,
          refreshToken: tokens.refreshToken,
          isAuthenticated: true,
        });
      },

      setTokens: (tokens: AuthTokens) => {
        set({
          accessToken: tokens.accessToken,
          refreshToken: tokens.refreshToken,
          isAuthenticated: !!tokens.accessToken,
        });
      },

      clearAuth: () => {
        set(initialState);
      },

      getAccessToken: () => {
        return get().accessToken;
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      // Only persist tokens, user will be fetched on app load
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
      // Rehydrate isAuthenticated from persisted tokens
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isAuthenticated = !!state.accessToken;
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
export const useAccessToken = () => useAuthStore((state) => state.accessToken);

/**
 * Action hooks
 */
export const useAuthActions = () =>
  useAuthStore((state) => ({
    setAuth: state.setAuth,
    setTokens: state.setTokens,
    clearAuth: state.clearAuth,
  }));

export default useAuthStore;
