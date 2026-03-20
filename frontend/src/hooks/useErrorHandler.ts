/**
 * useErrorHandler Hook
 *
 * Bridges async errors (useEffect, event handlers, promises) to the
 * nearest React ErrorBoundary.  Class-based error boundaries only catch
 * synchronous render errors — this hook fills the gap.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const throwError = useErrorHandler();
 *
 *   useEffect(() => {
 *     fetchData().catch(throwError);
 *   }, []);
 * }
 * ```
 */

import { useCallback, useState } from "react";

/**
 * Returns a function that, when called with an error, triggers the
 * nearest ErrorBoundary by re-throwing during render via setState.
 */
export function useErrorHandler(): (error: unknown) => void {
  const [, setState] = useState();

  return useCallback((error: unknown) => {
    setState(() => {
      throw error instanceof Error ? error : new Error(String(error));
    });
  }, []);
}
