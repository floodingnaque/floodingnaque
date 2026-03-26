/**
 * Authentication Store
 *
 * Zustand store for managing authentication state.
 * User, tokens, and auth flags are persisted to localStorage
 * so sessions survive page reloads. The 401-response interceptor
 * in api-client.ts handles expired access tokens automatically.
 */

import { getDefaultRoute } from "@/config/role-routes";
import { initializeAuthStore } from "@/lib/api-client";
import { postTabMessage } from "@/lib/tab-sync";
import type { User } from "@/types";
import { useMemo } from "react";
import { create } from "zustand";
import { createJSONStorage, devtools, persist } from "zustand/middleware";

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
  setAuth: (
    user: User,
    csrfToken?: string,
    accessToken?: string,
    refreshToken?: string,
  ) => void;
  /** Update the CSRF token (e.g. after refresh) */
  setCsrfToken: (csrfToken: string) => void;
  /** Update the access token (e.g. after refresh) */
  setAccessToken: (accessToken: string) => void;
  /** Clear all authentication data (logout) */
  clearAuth: () => void;
  /** Clear auth without broadcasting to other tabs */
  clearAuthSilent: () => void;
  /** Set access token without broadcasting to other tabs */
  setAccessTokenSilent: (accessToken: string) => void;
  /** Mark Zustand rehydration as complete */
  setHasHydrated: (v: boolean) => void;
  /** Get the role-appropriate redirect route for the current user */
  getRedirectRoute: () => string;
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
  devtools(
    persist(
      (set) => ({
        ...initialState,

        setAuth: (
          user: User,
          csrfToken?: string,
          accessToken?: string,
          refreshToken?: string,
        ) => {
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
          postTabMessage({ type: "AUTH_LOGOUT" });
        },

        /** Clear auth without broadcasting (called from tab-sync listener) */
        clearAuthSilent: () => {
          set({ ...initialState, hasHydrated: true });
        },

        /** Set access token without broadcasting (called from tab-sync listener) */
        setAccessTokenSilent: (accessToken: string) => {
          set({ accessToken });
        },

        setHasHydrated: (v: boolean) => {
          set({ hasHydrated: v });
        },

        getRedirectRoute: () => {
          const role = useAuthStore.getState().user?.role;
          return getDefaultRoute(role);
        },
      }),
      {
        name: "auth-storage",
        storage: createJSONStorage(() => localStorage),
        // Persist user metadata and tokens so sessions survive page reloads.
        // The access token is short-lived (15 min) and the response
        // interceptor automatically attempts a refresh on 401.
        partialize: (state) => ({
          user: state.user
            ? {
                id: state.user.id,
                role: state.user.role,
                name: state.user.name,
              }
            : null,
          accessToken: state.accessToken,
          refreshToken: state.refreshToken,
          isAuthenticated: state.isAuthenticated,
          csrfToken: state.csrfToken,
        }),
        // After rehydration: restore full auth state from persisted values.
        // If tokens were persisted, keep isAuthenticated as-is so the user
        // remains logged in across page reloads without a flash-to-login.
        onRehydrateStorage: () => (state) => {
          if (state) {
            // If we have a user and access token, stay authenticated.
            // If tokens expired, the response interceptor handles 401 → refresh.
            if (!state.user || !state.accessToken) {
              state.isAuthenticated = false;
            }
            state.hasHydrated = true;
          }
        },
      },
    ),
    { name: "auth-store", enabled: import.meta.env.DEV },
  ),
);

// Initialize the API client with the auth store reference
initializeAuthStore(useAuthStore);

// Initialize Supabase Realtime auth sync - forwards the JWT so
// RLS policies can identify the user across all roles.
import { initSupabaseAuth } from "@/lib/supabase";

{
  let prevToken = useAuthStore.getState().accessToken;
  initSupabaseAuth(
    // subscribe: listen for accessToken changes
    (cb) =>
      useAuthStore.subscribe((state) => {
        if (state.accessToken !== prevToken) {
          prevToken = state.accessToken;
          cb(state.accessToken);
        }
      }),
    // getToken: read current token
    () => useAuthStore.getState().accessToken,
  );
}

/**
 * Selector hooks for common auth state
 */
export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () =>
  useAuthStore((state) => state.isAuthenticated);
export const useHasHydrated = () => useAuthStore((state) => state.hasHydrated);
export const useCsrfToken = () => useAuthStore((state) => state.csrfToken);

/**
 * Action hooks - each selector returns a stable reference to avoid
 * defeating React.memo / shallow-equality checks.
 */
export const useSetAuth = () => useAuthStore((state) => state.setAuth);
export const useSetCsrfToken = () =>
  useAuthStore((state) => state.setCsrfToken);
export const useClearAuth = () => useAuthStore((state) => state.clearAuth);
export const useUserRole = () => useAuthStore((s) => s.user?.role);

/**
 * Combined actions object - kept for backward compatibility but
 * consumers that only need one action should prefer the individual hooks
 * above to avoid creating a new object on every render.
 */
export const useAuthActions = () => {
  const setAuth = useSetAuth();
  const setCsrfToken = useSetCsrfToken();
  const clearAuth = useClearAuth();
  return useMemo(
    () => ({ setAuth, setCsrfToken, clearAuth }),
    [setAuth, setCsrfToken, clearAuth],
  );
};

export default useAuthStore;
