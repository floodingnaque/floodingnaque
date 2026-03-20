/**
 * Vercel Edge Middleware - CSP Nonce Injection
 *
 * Generates a cryptographically random nonce per request and injects it into
 * the Content-Security-Policy header, replacing blanket 'unsafe-inline' with
 * granular nonce-based allowlisting for scripts.
 *
 * HOW IT WORKS
 * ────────────
 * 1. On every request, `crypto.randomUUID()` produces a unique nonce.
 * 2. The nonce is embedded in `script-src` via `'nonce-<value>'`.
 *    Modern browsers (CSP Level 2+) then IGNORE the co-existing
 *    `'unsafe-inline'` fallback, which is retained only for legacy
 *    browsers that do not support nonces.
 * 3. `style-src` keeps `'unsafe-inline'` because Radix UI primitives
 *    inject inline `style` attributes at runtime (e.g., popovers,
 *    dialogs, tooltips) and Tailwind CSS uses runtime class injection.
 *    Nonces cannot be applied to element-level `style` attributes
 *    per the CSP specification - only to `<style>` / `<link>` elements.
 * 4. The nonce is passed to the application via the `X-Nonce` response
 *    header so that SSR templates or client hydration can read it.
 *
 * FRAMEWORK NOTE
 * ──────────────
 * Vercel auto-detects this middleware for Next.js, Nuxt, SvelteKit,
 * and Astro. For a Vite static build, this file is NOT executed
 * automatically. To activate it:
 *   • Migrate to one of the supported SSR frameworks, OR
 *   • Use the Vercel Build Output API v3 to wire it manually.
 *
 * Until then, the static CSP in vercel.json serves as the production
 * policy. This middleware is kept as ready-to-activate infrastructure.
 *
 * @see https://vercel.com/docs/functions/edge-middleware
 * @see https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
 */

export const config = {
  // Match all routes except static assets (immutable-cached via vercel.json)
  matcher: [
    "/((?!assets/|favicon\\.ico|manifest\\.json|robots\\.txt|og-image\\.png).*)",
  ],
};

export default function middleware(_request: Request): Response {
  // eslint-disable-line @typescript-eslint/no-unused-vars
  const nonce = crypto.randomUUID();

  const csp = [
    "default-src 'self'",
    // Nonce for scripts - 'unsafe-inline' is ignored by CSP 2+ when nonce is present
    `script-src 'self' 'nonce-${nonce}' 'unsafe-inline'`,
    // 'unsafe-inline' required for Radix UI style attributes & Tailwind runtime
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "connect-src 'self' https:",
    "font-src 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "upgrade-insecure-requests",
  ].join("; ");

  // The next() helper from @vercel/edge forwards the request to the origin
  // and merges the provided headers into the response. Since this middleware
  // is framework-gated, we use the standard Response constructor so the file
  // has zero runtime dependencies and can be validated by TypeScript alone.
  //
  // When activating for a supported framework, replace the body below with:
  //
  //   import { next } from "@vercel/edge";
  //   return next({ headers: { "Content-Security-Policy": csp, "X-Nonce": nonce } });
  //

  return new Response(null, {
    status: 200,
    headers: {
      "Content-Security-Policy": csp,
      "X-Nonce": nonce,
    },
  });
}
