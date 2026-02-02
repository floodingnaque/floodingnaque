/**
 * usePrediction Hook
 *
 * React Query mutation hook for flood risk prediction.
 * Provides loading, error, and success states for prediction requests.
 */

import { useMutation, type UseMutationOptions } from '@tanstack/react-query';
import { predictionApi } from '../services/predictionApi';
import type { PredictionRequest, PredictionResponse, ApiError } from '@/types';

/**
 * Options for the usePrediction hook
 */
export interface UsePredictionOptions {
  /** Callback when prediction succeeds */
  onSuccess?: (data: PredictionResponse) => void;
  /** Callback when prediction fails */
  onError?: (error: ApiError) => void;
}

/**
 * usePrediction hook for flood risk prediction
 *
 * @param options - Optional callbacks for success and error handling
 * @returns Mutation object with predict function and state
 *
 * @example
 * const { mutate: predict, isPending, isError, error } = usePrediction({
 *   onSuccess: (result) => console.log('Prediction:', result),
 * });
 *
 * predict({ temperature: 298.15, humidity: 85, precipitation: 50, wind_speed: 15 });
 */
export function usePrediction(options?: UsePredictionOptions) {
  const mutationOptions: UseMutationOptions<
    PredictionResponse,
    ApiError,
    PredictionRequest
  > = {
    mutationFn: (data: PredictionRequest) => predictionApi.predict(data),
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  };

  const mutation = useMutation(mutationOptions);

  return {
    /** Trigger a prediction request */
    predict: mutation.mutate,
    /** Trigger a prediction request and return a promise */
    predictAsync: mutation.mutateAsync,
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

export default usePrediction;
