/**
 * Security Utilities
 *
 * Client-side input sanitisation and URL validation helpers.
 * These are a defence-in-depth layer - the backend MUST also
 * validate and sanitise all inputs independently.
 */

// ---------------------------------------------------------------------------
// Input sanitisation
// ---------------------------------------------------------------------------

/**
 * Map of characters that must be escaped in HTML contexts.
 */
const HTML_ESCAPE_MAP: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#x27;',
  '/': '&#x2F;',
};

const HTML_ESCAPE_RE = /[&<>"'/]/g;

/**
 * Escape HTML-significant characters to prevent XSS when
 * interpolating user-supplied strings into the DOM.
 *
 * @example
 * ```ts
 * sanitizeInput('<script>alert(1)</script>');
 * // → '&lt;script&gt;alert(1)&lt;&#x2F;script&gt;'
 * ```
 */
export function sanitizeInput(str: string): string {
  if (typeof str !== 'string') return '';
  return str.replace(HTML_ESCAPE_RE, (char) => HTML_ESCAPE_MAP[char] || char);
}

// ---------------------------------------------------------------------------
// URL validation
// ---------------------------------------------------------------------------

/** Schemes considered safe for user-provided links. */
const SAFE_SCHEMES = new Set(['http:', 'https:', 'mailto:']);

/**
 * Validate that a URL string is safe to navigate to or render as an `<a>` href.
 * Rejects `javascript:`, `data:`, and other dangerous schemes.
 *
 * @returns `true` when the URL is well-formed and uses a safe scheme.
 *
 * @example
 * ```ts
 * validateUrl('https://example.com');  // true
 * validateUrl('javascript:alert(1)');  // false
 * ```
 */
export function validateUrl(url: string): boolean {
  try {
    const parsed = new URL(url, window.location.origin);
    return SAFE_SCHEMES.has(parsed.protocol);
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Content-Security-Policy nonce helper
// ---------------------------------------------------------------------------

/**
 * Generate a cryptographically random nonce for inline scripts/styles.
 * Useful when building CSP headers dynamically on a SSR server -
 * on the client, this is mainly here for completeness.
 */
export function generateNonce(length = 16): string {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return btoa(String.fromCharCode(...array));
}
