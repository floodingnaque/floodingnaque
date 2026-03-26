/**
 * API Client
 *
 * Axios-based HTTP client with httpOnly cookie authentication,
 * CSRF token injection, automatic token refresh via cookies,
 * and standardised error handling.
 */

import { API_CONFIG } from "@/config/api.config";
import type { ApiError } from "@/types";
import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import { toast } from "sonner";

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
    "Content-Type": "application/json",
  },
});

// ---------------------------------------------------------------------------
// Request deduplication – coalesce identical in-flight GET requests
// ---------------------------------------------------------------------------

const inflightRequests = new Map<string, Promise<AxiosResponse>>();

function dedupKey(config: AxiosRequestConfig): string | null {
  const method = (config.method ?? "get").toLowerCase();
  if (method !== "get") return null;
  const url = `${config.baseURL ?? ""}${config.url ?? ""}`;
  const params = config.params ? JSON.stringify(config.params) : "";
  return `${method}:${url}:${params}`;
}

// ---------------------------------------------------------------------------
// Request interceptor – attach CSRF token for state-changing requests
// ---------------------------------------------------------------------------

const CSRF_METHODS = new Set(["post", "put", "patch", "delete"]);

axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Attach a unique correlation ID for end-to-end request tracing
    if (config.headers) {
      config.headers["X-Correlation-ID"] = crypto.randomUUID();
    }

    // Attach JWT access token as Authorization header
    const accessToken = authStore?.getState().accessToken;
    if (accessToken && config.headers) {
      config.headers["Authorization"] = `Bearer ${accessToken}`;
    }

    // Attach CSRF token for state-changing requests
    const method = (config.method ?? "").toLowerCase();
    if (CSRF_METHODS.has(method) && config.headers) {
      const csrfToken = authStore?.getState().csrfToken;
      if (csrfToken) {
        config.headers["X-CSRF-Token"] = csrfToken;
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
    if (error.response?.status === 401 && !originalRequest._retry) {
      // If there's no refresh token, skip the refresh attempt entirely
      const currentRefreshToken = authStore?.getState().refreshToken;
      if (!currentRefreshToken) {
        authStore?.getState().clearAuth();
        return Promise.reject(error);
      }

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
        const doRefresh = async () => {
          const refreshToken = authStore?.getState().refreshToken;
          const { data } = await axios.post(
            `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.auth.refresh}`,
            { refresh_token: refreshToken },
            { withCredentials: true },
          );

          if (data.access_token) {
            authStore?.getState().setAccessToken(data.access_token);
          }
          if (data.csrf_token) {
            authStore?.getState().setCsrfToken(data.csrf_token);
          }
        };

        // Use Web Locks if available for cross-tab coordination
        if (navigator.locks) {
          await navigator.locks.request(
            "floodingnaque-auth-refresh",
            { mode: "exclusive" },
            doRefresh,
          );
        } else {
          await doRefresh();
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

    // Cancelled requests (e.g. React Query aborting on unmount during
    // navigation) must not be treated as network failures.
    if (axios.isCancel(error) || error.code === "ERR_CANCELED") {
      const cancelledError: ApiError = {
        code: "REQUEST_CANCELED",
        message: "Request was canceled",
        status: 0,
      };
      return Promise.reject(cancelledError);
    }

    // Normalise error payload
    // Backend RFC 7807 responses use shape: { success, error: { code, detail, status, … } }
    // Extract the nested error object and map `detail` → `message` for ApiError compat.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw = error.response?.data as Record<string, any> | undefined;
    let apiError: ApiError;

    if (raw?.error && typeof raw.error === "object") {
      apiError = {
        code: raw.error.code ?? "UNKNOWN_ERROR",
        message:
          raw.error.detail ?? raw.error.title ?? "An unexpected error occurred",
        status: raw.error.status ?? error.response?.status,
        details: raw.error.details,
        field_errors: raw.error.errors,
        timestamp: raw.error.timestamp,
      };
    } else {
      apiError = {
        code: raw?.code ?? "NETWORK_ERROR",
        message:
          raw?.message ?? error.message ?? "An unexpected error occurred",
        status: raw?.status ?? error.response?.status,
      };
    }

    return Promise.reject(apiError);
  },
);

// ---------------------------------------------------------------------------
// Global error toast notifications
// ---------------------------------------------------------------------------

// Statuses that should NOT trigger a global toast (handled by callers)
const SILENT_STATUSES = new Set([401, 422]);

axiosInstance.interceptors.response.use(undefined, (error: unknown) => {
  const apiError = error as ApiError;
  const status = apiError?.status;

  // Cancelled requests (navigation, unmount) - never show a toast
  if (apiError?.code === "REQUEST_CANCELED") {
    return Promise.reject(error);
  }

  if (status && SILENT_STATUSES.has(status)) {
    return Promise.reject(error);
  }

  if (!status) {
    toast.error("Connection lost", {
      description:
        "Unable to reach the server. This may be a temporary network issue - the app will retry automatically.",
      id: "network-error",
      duration: 8000,
    });
  } else if (status === 429) {
    toast.warning("Too many requests", {
      description: "Please wait a moment before trying again.",
      id: "rate-limit",
      duration: 5000,
    });
  } else if (status >= 500) {
    toast.error("Server error", {
      description:
        apiError.message ||
        "Something went wrong on our end. Please try again in a few moments.",
      id: `server-error-${status}`,
      duration: 6000,
    });
  }

  return Promise.reject(error);
});

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
    const key = dedupKey({ ...config, url, method: "get" });
    if (key) {
      const inflight = inflightRequests.get(key);
      if (inflight) return inflight.then((r) => r.data as T);
      const promise = axiosInstance.get<T>(url, config);
      inflightRequests.set(key, promise as Promise<AxiosResponse>);
      try {
        const response = await promise;
        return response.data;
      } finally {
        inflightRequests.delete(key);
      }
    }
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
