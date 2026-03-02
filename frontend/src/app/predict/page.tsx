/**
 * Prediction Page
 *
 * Main page for flood risk prediction functionality.
 * Shows either the prediction form or the result based on state.
 * Falls back to the most recent cached prediction when offline.
 */

import { useState, useEffect } from 'react';
import { CloudRain, ShieldAlert } from 'lucide-react';

import { PredictionForm } from '@/features/flooding/components/PredictionForm';
import { PredictionResult } from '@/features/flooding/components/PredictionResult';
import { StaleDataBanner } from '@/components/feedback/StaleDataBanner';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';
import { getCachedPredictions } from '@/lib/offlineCache';
import type { PredictionResponse } from '@/types';

/**
 * PredictPage component - Main prediction interface
 */
export default function PredictPage() {
  const [predictionResult, setPredictionResult] = useState<PredictionResponse | null>(null);
  const [offlineCachedAt, setOfflineCachedAt] = useState<string | null>(null);
  const { isOnline } = useNetworkStatus();

  // When offline and no result is showing, load the most recent cached prediction
  useEffect(() => {
    if (!isOnline && !predictionResult) {
      getCachedPredictions(1).then((cached) => {
        if (cached.length > 0) {
          setPredictionResult(cached[0].data);
          setOfflineCachedAt(cached[0].cachedAt);
        }
      });
    }
    if (isOnline) {
      setOfflineCachedAt(null);
    }
  }, [isOnline, predictionResult]);

  /**
   * Handle successful prediction
   */
  const handlePredictionSuccess = (result: PredictionResponse) => {
    setPredictionResult(result);
  };

  /**
   * Reset to show form again
   */
  const handleReset = () => {
    setPredictionResult(null);
  };

  return (
    <div className="container max-w-4xl py-8 px-4">
      {/* Page Header */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-4">
          {predictionResult ? (
            <ShieldAlert className="h-10 w-10 text-foreground" />
          ) : (
            <CloudRain className="h-10 w-10 text-foreground" />
          )}
          <h1 className="text-3xl font-bold tracking-tight">
            Flood Risk Prediction
          </h1>
        </div>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          {predictionResult
            ? 'View your flood risk assessment below. You can make another prediction or view your prediction history.'
            : 'Enter current weather conditions to assess flood risk in your area. Our machine learning model analyzes multiple factors to provide accurate predictions.'}
        </p>
      </div>

      {/* Conditional Content */}
      {offlineCachedAt && predictionResult && (
        <StaleDataBanner cachedAt={offlineCachedAt} />
      )}

      {predictionResult ? (
        <PredictionResult
          result={predictionResult}
          onReset={handleReset}
        />
      ) : (
        <PredictionForm onSuccess={handlePredictionSuccess} />
      )}
    </div>
  );
}
