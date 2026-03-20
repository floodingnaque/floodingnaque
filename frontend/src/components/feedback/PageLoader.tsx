/**
 * PageLoader Component
 *
 * Full-page loading indicator used as a Suspense fallback
 * when lazy-loaded route components are being fetched.
 */

import { Loader2 } from "lucide-react";

/**
 * Displays a centered spinner filling the content area.
 * Designed for use with React.lazy() + Suspense at the route level.
 */
export function PageLoader() {
  return (
    <div
      className="flex min-h-[60vh] items-center justify-center"
      role="status"
      aria-live="polite"
      aria-label="Loading page"
    >
      <div className="flex flex-col items-center gap-4">
        {/* Top progress bar */}
        <div className="w-48 h-1 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-primary rounded-full animate-[loading-bar_1.5s_ease-in-out_infinite]" />
        </div>
        <Loader2
          className="h-8 w-8 animate-spin text-primary"
          aria-hidden="true"
        />
        <p className="text-sm font-medium text-muted-foreground">Loading…</p>
        <span className="sr-only">Loading page</span>
      </div>
    </div>
  );
}

export default PageLoader;
