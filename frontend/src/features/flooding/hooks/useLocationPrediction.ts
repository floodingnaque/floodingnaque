/**
 * useLocationPrediction Hook
 *
 * React Query mutation hook for location-based flood risk prediction.
 * Sends GPS coordinates to the backend which fetches weather data automatically.
 */

import { useMutation, type UseMutationOptions } from '@tanstack/react-query';
import { predictionApi } from '../services/predictionApi';
import type {
  LocationPredictionRequest,
  PredictionResponse,
  ApiError,
} from '@/types';

/**
 * Options for the useLocationPrediction hook
 */
export interface UseLocationPredictionOptions {
  /** Callback when prediction succeeds */
  onSuccess?: (data: PredictionResponse) => void;
  /** Callback when prediction fails */
  onError?: (error: ApiError) => void;
}

/**
 * useLocationPrediction hook for coordinate-based flood risk prediction
 *
 * @param options - Optional callbacks for success and error handling
 * @returns Mutation object with predict function and state
 *
 * @example
 * const { predictByLocation, isPending } = useLocationPrediction({
 *   onSuccess: (result) => console.log('Risk:', result.risk_label),
 * });
 *
 * predictByLocation({ latitude: 14.4793, longitude: 121.0198 });
 */
export function useLocationPrediction(
  options?: UseLocationPredictionOptions
) {
  const mutationOptions: UseMutationOptions<
    PredictionResponse,
    ApiError,
    LocationPredictionRequest
  > = {
    mutationFn: (data: LocationPredictionRequest) =>
      predictionApi.predictByLocation(data),
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  };

  const mutation = useMutation(mutationOptions);

  return {
    /** Trigger a location-based prediction request */
    predictByLocation: mutation.mutate,
    /** Trigger a location-based prediction and return a promise */
    predictByLocationAsync: mutation.mutateAsync,
    /** Whether a prediction is in progress */
    isPending: mutation.isPending,
    /** Whether the last prediction succeeded */
    isSuccess: mutation.isSuccess,
    /** Whether the last prediction failed */
    isError: mutation.isError,
    /** Error from the last failed prediction */
    error: mutation.error,
    /** Data from the last successful prediction */
    data: mutation.data,
    /** Reset the mutation state */
    reset: mutation.reset,
  };
}

export default useLocationPrediction;
