/**
 * Secure UUID v4 generator — works in all contexts.
 *
 * `crypto.randomUUID()` requires a **secure context** (HTTPS or localhost).
 * When the app is accessed over plain HTTP on a LAN IP (e.g. 192.168.x.x:3000),
 * the browser throws `TypeError: crypto.randomUUID is not a function`.
 *
 * This utility falls back to `crypto.getRandomValues()` which is available
 * in all modern browsers regardless of secure context.
 */

function fallbackUUID(): string {
  // RFC 4122 version 4 UUID from crypto.getRandomValues()
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);

  // Set version (4) and variant (10xx) bits per RFC 4122
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join(
    "",
  );
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/**
 * Generate a cryptographically random UUID v4 string.
 *
 * Uses `crypto.randomUUID()` when available (secure contexts),
 * otherwise falls back to an equivalent `crypto.getRandomValues()` implementation.
 */
export function uuid(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return fallbackUUID();
}
