/**
 * Hooks Index
 *
 * Re-exports all custom hooks for convenient imports.
 */

export {
  useIsDesktop,
  useIsMobile,
  useIsTablet,
  useMediaQuery,
  usePrefersDarkMode,
  usePrefersReducedMotion,
} from "./useMediaQuery";

export {
  useGeolocation,
  type GeolocationCoordinates,
  type UseGeolocationReturn,
} from "./useGeolocation";

export { usePushNotifications } from "./usePushNotifications";

export { useNotificationAutoPrompt } from "./useNotificationAutoPrompt";

export { useNetworkStatus } from "./useNetworkStatus";
