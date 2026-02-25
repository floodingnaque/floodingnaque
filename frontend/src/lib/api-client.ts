/**
 * API Client
 *
 * Axios-based HTTP client with httpOnly cookie authentication,
 * CSRF token injection, automatic token refresh via cookies,
 * and standardised error handling.
 */

import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios';
import { API_CONFIG } from '@/config/api.config';
import type { ApiError } from '@/types';

// ---------------------------------------------------------------------------
// Auth store reference (set at runtime to avoid circular imports)
// ---------------------------------------------------------------------------

type AuthStoreApi = {
  getState: () => {
    csrfToken: string | null;
    accessToken: string | null;
    refreshToken: string | null;
    clearAuth: () => void;
    setCsrfToken: (csrfToken: string) => void;
    setAccessToken: (accessToken: string) => void;
  };
};

let authStore: AuthStoreApi | null = null;

/**
 * Called once from `authStore.ts` after the store is created, so
 * the API client can read / set state without a circular dependency.
 */
export function initializeAuthStore(store: AuthStoreApi): void {
  authStore = store;
}

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_CONFIG.baseUrl,
  timeout: API_CONFIG.timeout,
  withCredentials: true, // Send httpOnly cookies automatically
  headers: {
    'Content-Type': 'application/json',
  },
});

// ---------------------------------------------------------------------------
// Request interceptor – attach CSRF token for state-changing requests
// ---------------------------------------------------------------------------

const CSRF_METHODS = new Set(['post', 'put', 'patch', 'delete']);

axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Attach JWT access token as Authorization header
    const accessToken = authStore?.getState().accessToken;
    if (accessToken && config.headers) {
      config.headers['Authorization'] = `Bearer ${accessToken}`;
    }

    // Attach CSRF token for state-changing requests
    const method = (config.method ?? '').toLowerCase();
    if (CSRF_METHODS.has(method) && config.headers) {
      const csrfToken = authStore?.getState().csrfToken;
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken;
      }
    }
    return config;
  },
  (error: unknown) => Promise.reject(error),
);

// ---------------------------------------------------------------------------
// Response interceptor – normalise errors & (optional) token refresh
// ---------------------------------------------------------------------------

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string | null) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
}

axiosInstance.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // 401 → attempt silent refresh (once) via httpOnly refresh cookie
    if (
      error.response?.status === 401 &&
      !originalRequest._retry
    ) {
      if (isRefreshing) {
        // Queue this request while another refresh is in-flight
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => {
          return axiosInstance(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Send the refresh token in the request body
        const refreshToken = authStore?.getState().refreshToken;
        const { data } = await axios.post(
          `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.auth.refresh}`,
          { refresh_token: refreshToken },
          { withCredentials: true },
        );

        // Update the access token in the store
        if (data.access_token) {
          authStore?.getState().setAccessToken(data.access_token);
        }

        // If the server returns a new CSRF token, update the store
        if (data.csrf_token) {
          authStore?.getState().setCsrfToken(data.csrf_token);
        }

        processQueue(null, null);
        return axiosInstance(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        authStore?.getState().clearAuth();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Normalise error payload
    const apiError: ApiError = error.response?.data ?? {
      code: 'NETWORK_ERROR',
      message: error.message || 'An unexpected error occurred',
      status: error.response?.status,
    };

    return Promise.reject(apiError);
  },
);

// ---------------------------------------------------------------------------
// Typed helper methods
// ---------------------------------------------------------------------------

/**
 * Typed HTTP client wrapping the shared Axios instance.
 *
 * Every method returns the **response data** directly (not the
 * AxiosResponse wrapper) so callers can write:
 *
 * ```ts
 * const user = await api.get<User>('/api/v1/auth/me');
 * ```
 */
export const api = {
  get: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    const response = await axiosInstance.get<T>(url, config);
    return response.data;
  },

  post: async <T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<T> => {
    const response = await axiosInstance.post<T>(url, data, config);
    return response.data;
  },

  put: async <T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<T> => {
    const response = await axiosInstance.put<T>(url, data, config);
    return response.data;
  },

  patch: async <T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<T> => {
    const response = await axiosInstance.patch<T>(url, data, config);
    return response.data;
  },

  delete: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    const response = await axiosInstance.delete<T>(url, config);
    return response.data;
  },
};

export default api;
