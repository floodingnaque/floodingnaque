/**
 * usePrediction Hook
 *
 * React Query mutation hook for flood risk prediction.
 * Provides loading, error, and success states for prediction requests.
 * Caches successful predictions to IndexedDB for offline access.
 */

import { cachePrediction } from "@/lib/offlineCache";
import type { ApiError, PredictionRequest, PredictionResponse } from "@/types";
import { useMutation, type UseMutationOptions } from "@tanstack/react-query";
import { useOptimistic, useTransition } from "react";
import { toast } from "sonner";
import { predictionApi } from "../services/predictionApi";

// ---------------------------------------------------------------------------
// Local risk estimation (mirrors backend RiskClassifier thresholds)
// ---------------------------------------------------------------------------

type RiskLevel = "Safe" | "Alert" | "Critical";

function estimateRiskLocally(data: PredictionRequest): RiskLevel {
  const precip = data.precipitation ?? 0;
  if (precip > 20) return "Critical";
  if (precip > 5) return "Alert";
  return "Safe";
}

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
  const [optimisticRisk, setOptimisticRisk] =
    useOptimistic<RiskLevel | null>(null);
  const [isPendingTransition, startTransition] = useTransition();

  const mutationOptions: UseMutationOptions<
    PredictionResponse,
    ApiError,
    PredictionRequest
  > = {
    mutationFn: (data: PredictionRequest) => predictionApi.predict(data),
    onSuccess: (data) => {
      // Persist to IndexedDB for offline access
      cachePrediction(data)
        .then(() =>
          toast.success("Prediction saved for offline access", {
            duration: 2000,
          }),
        )
        .catch(() => {});
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  };

  const mutation = useMutation(mutationOptions);

  /**
   * Predict with optimistic risk level update.
   * Immediately shows estimated risk, then replaces with server result.
   */
  const predictOptimistic = (data: PredictionRequest) => {
    startTransition(() => {
      setOptimisticRisk(estimateRiskLocally(data));
      mutation.mutate(data);
    });
  };

  return {
    /** Trigger a prediction request */
    predict: mutation.mutate,
    /** Trigger prediction with optimistic risk display */
    predictOptimistic,
    /** Trigger a prediction request and return a promise */
    predictAsync: mutation.mutateAsync,
    /** Whether a prediction is in progress */
    isPending: mutation.isPending || isPendingTransition,
    /** Whether the last prediction succeeded */
    isSuccess: mutation.isSuccess,
    /** Whether the last prediction failed */
    isError: mutation.isError,
    /** Error from the last failed prediction */
    error: mutation.error,
    /** Data from the last successful prediction */
    data: mutation.data,
    /** Optimistic risk level (shown before server confirms) */
    optimisticRisk,
    /** Reset the mutation state */
    reset: mutation.reset,
  };
}

export default usePrediction;
