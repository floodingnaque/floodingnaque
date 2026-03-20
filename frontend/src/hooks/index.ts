/**
 * Hooks Index
 *
 * Re-exports all custom hooks for convenient imports.
 */

export {
  useMediaQuery,
  useIsMobile,
  useIsTablet,
  useIsDesktop,
  usePrefersDarkMode,
  usePrefersReducedMotion,
} from './useMediaQuery';

export {
  useGeolocation,
  type GeolocationCoordinates,
  type UseGeolocationReturn,
} from './useGeolocation';
