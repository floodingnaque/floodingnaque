/**
 * RouteProgress - Top progress bar for route transitions
 *
 * Shows a slim animated bar at the top of the viewport during
 * Suspense loading (lazy route transitions). Uses refs + DOM
 * manipulation to avoid cascading renders.
 */

import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

export function RouteProgress() {
  const location = useLocation();
  const barRef = useRef<HTMLDivElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const prevPath = useRef(location.pathname);

  useEffect(() => {
    if (prevPath.current === location.pathname) return;
    prevPath.current = location.pathname;

    const wrap = wrapRef.current;
    const bar = barRef.current;
    if (!wrap || !bar) return;

    wrap.style.opacity = "1";
    bar.style.transition = "width 0.15s ease-out";
    bar.style.width = "30%";

    const fast = setTimeout(() => {
      bar.style.transition = "width 0.3s ease-out";
      bar.style.width = "70%";
    }, 100);

    const done = setTimeout(() => {
      bar.style.width = "100%";
      setTimeout(() => {
        wrap.style.opacity = "0";
        bar.style.width = "0%";
      }, 200);
    }, 300);

    return () => {
      clearTimeout(fast);
      clearTimeout(done);
    };
  }, [location.pathname]);

  return (
    <div
      ref={wrapRef}
      className="fixed top-0 left-0 right-0 z-100 h-0.5 bg-transparent transition-opacity duration-200"
      style={{ opacity: 0 }}
      role="progressbar"
      aria-label="Page loading"
    >
      <div ref={barRef} className="h-full bg-primary" style={{ width: "0%" }} />
    </div>
  );
}
