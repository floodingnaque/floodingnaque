import { useEffect, useState } from "react";

/**
 * Returns `true` when the browser tab is visible, `false` when hidden.
 * Useful for pausing polling when the user switches to another tab.
 */
export function usePageVisibility(): boolean {
  const [visible, setVisible] = useState(
    () =>
      typeof document !== "undefined" && document.visibilityState === "visible",
  );

  useEffect(() => {
    const handler = () => setVisible(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, []);

  return visible;
}
