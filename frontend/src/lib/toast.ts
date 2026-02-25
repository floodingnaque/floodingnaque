/**
 * Toast Helpers
 *
 * Thin wrapper around Sonner `toast()` with consistent defaults:
 *   - success: green, auto-dismiss 3 s
 *   - error:   red, manual dismiss or 5 s
 *   - info:    blue, auto-dismiss 3 s
 *   - warning: amber, auto-dismiss 4 s
 *
 * Use these instead of calling Sonner directly so durations
 * and styles stay project-wide consistent.
 *
 * @example
 * ```ts
 * import { showToast } from '@/lib/toast';
 *
 * showToast.success('Prediction saved');
 * showToast.error('Network request failed');
 * ```
 */

import { toast, type ExternalToast } from 'sonner';

// ---------------------------------------------------------------------------
// Default durations (ms)
// ---------------------------------------------------------------------------
const DURATION_SUCCESS = 3_000;
const DURATION_ERROR = 5_000;
const DURATION_INFO = 3_000;
const DURATION_WARNING = 4_000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function success(message: string, options?: ExternalToast) {
  return toast.success(message, {
    duration: DURATION_SUCCESS,
    ...options,
  });
}

function error(message: string, options?: ExternalToast) {
  return toast.error(message, {
    duration: DURATION_ERROR,
    ...options,
  });
}

function info(message: string, options?: ExternalToast) {
  return toast.info(message, {
    duration: DURATION_INFO,
    ...options,
  });
}

function warning(message: string, options?: ExternalToast) {
  return toast.warning(message, {
    duration: DURATION_WARNING,
    ...options,
  });
}

/**
 * Dismiss a specific toast or all toasts.
 */
function dismiss(id?: string | number) {
  toast.dismiss(id);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export const showToast = {
  success,
  error,
  info,
  warning,
  dismiss,
} as const;

export default showToast;
