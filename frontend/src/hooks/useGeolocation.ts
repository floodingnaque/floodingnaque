/**
 * useGeolocation Hook
 *
 * Wraps the HTML5 Geolocation API (navigator.geolocation) with React state
 * management. Provides loading, error, and coordinate states.
 *
 * No GPS API key required — uses the browser's built-in Geolocation API.
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API
 */

import { useState, useCallback } from 'react';

/**
 * Geolocation coordinates returned by the hook
 */
export interface GeolocationCoordinates {
  latitude: number;
  longitude: number;
  accuracy: number; // meters
}

/**
 * Geolocation hook state
 */
export interface UseGeolocationReturn {
  /** Current coordinates (null until requested and resolved) */
  coordinates: GeolocationCoordinates | null;
  /** Whether the geolocation request is in progress */
  isLocating: boolean;
  /** Error message if geolocation failed */
  error: string | null;
  /** Whether the browser supports geolocation */
  isSupported: boolean;
  /** Request the user's current position */
  requestLocation: () => void;
  /** Clear coordinates and error state */
  reset: () => void;
}

/**
 * Human-readable error messages for GeolocationPositionError codes
 */
function getGeolocationErrorMessage(error: GeolocationPositionError): string {
  switch (error.code) {
    case error.PERMISSION_DENIED:
      return 'Location permission denied. Please allow location access in your browser settings.';
    case error.POSITION_UNAVAILABLE:
      return 'Location information is unavailable. Please try again later.';
    case error.TIMEOUT:
      return 'Location request timed out. Please try again.';
    default:
      return 'An unknown error occurred while retrieving your location.';
  }
}

/**
 * useGeolocation — React hook for HTML5 Geolocation API
 *
 * @param options - Optional PositionOptions (enableHighAccuracy, timeout, maximumAge)
 * @returns Geolocation state and request function
 *
 * @example
 * const { coordinates, isLocating, error, requestLocation } = useGeolocation();
 *
 * <button onClick={requestLocation} disabled={isLocating}>
 *   {isLocating ? 'Locating...' : 'Share Location'}
 * </button>
 *
 * {coordinates && <p>Lat: {coordinates.latitude}, Lon: {coordinates.longitude}</p>}
 */
export function useGeolocation(
  options?: PositionOptions
): UseGeolocationReturn {
  const [coordinates, setCoordinates] =
    useState<GeolocationCoordinates | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSupported =
    typeof navigator !== 'undefined' && 'geolocation' in navigator;

  const requestLocation = useCallback(() => {
    if (!isSupported) {
      setError('Geolocation is not supported by your browser.');
      return;
    }

    setIsLocating(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoordinates({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
        setIsLocating(false);
      },
      (positionError) => {
        setError(getGeolocationErrorMessage(positionError));
        setIsLocating(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000, // 5 minutes cache
        ...options,
      }
    );
  }, [isSupported, options]);

  const reset = useCallback(() => {
    setCoordinates(null);
    setError(null);
    setIsLocating(false);
  }, []);

  return {
    coordinates,
    isLocating,
    error,
    isSupported,
    requestLocation,
    reset,
  };
}

export default useGeolocation;
