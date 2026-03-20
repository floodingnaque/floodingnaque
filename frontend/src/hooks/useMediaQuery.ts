/**
 * useMediaQuery Hook
 *
 * Custom React hook for responsive design that tracks
 * whether a CSS media query matches.
 */

import { useState, useEffect, useCallback } from 'react';

/**
 * Hook to track whether a media query matches.
 *
 * @param query - CSS media query string (e.g., '(min-width: 768px)')
 * @returns boolean indicating if the media query currently matches
 *
 * @example
 * // Check if screen is at least tablet size
 * const isTablet = useMediaQuery('(min-width: 768px)');
 *
 * @example
 * // Check for dark mode preference
 * const prefersDark = useMediaQuery('(prefers-color-scheme: dark)');
 *
 * @example
 * // Check for reduced motion preference
 * const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
 */
export function useMediaQuery(query: string): boolean {
  // Initialize state with the current match status
  // Use a function to avoid calling matchMedia on SSR
  const getMatches = useCallback((): boolean => {
    // Prevent SSR issues
    if (typeof window === 'undefined') {
      return false;
    }
    return window.matchMedia(query).matches;
  }, [query]);

  const [matches, setMatches] = useState<boolean>(getMatches);

  useEffect(() => {
    // Prevent SSR issues
    if (typeof window === 'undefined') {
      return;
    }

    const mediaQueryList = window.matchMedia(query);

    // Update state with current value
    const updateMatches = () => {
      setMatches(mediaQueryList.matches);
    };

    // Set initial value
    updateMatches();

    // Modern browsers support addEventListener
    // Legacy browsers might need addListener
    if (mediaQueryList.addEventListener) {
      mediaQueryList.addEventListener('change', updateMatches);
    } else {
      // Fallback for older browsers
      mediaQueryList.addListener(updateMatches);
    }

    // Cleanup listener on unmount or query change
    return () => {
      if (mediaQueryList.removeEventListener) {
        mediaQueryList.removeEventListener('change', updateMatches);
      } else {
        // Fallback for older browsers
        mediaQueryList.removeListener(updateMatches);
      }
    };
  }, [query]);

  return matches;
}

// Preset breakpoint hooks for convenience
export const useIsMobile = () => useMediaQuery('(max-width: 639px)');
export const useIsTablet = () => useMediaQuery('(min-width: 640px) and (max-width: 1023px)');
export const useIsDesktop = () => useMediaQuery('(min-width: 1024px)');
export const usePrefersDarkMode = () => useMediaQuery('(prefers-color-scheme: dark)');
export const usePrefersReducedMotion = () => useMediaQuery('(prefers-reduced-motion: reduce)');

export default useMediaQuery;
