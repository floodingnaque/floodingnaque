/**
 * usePrediction Hook Tests
 *
 * Tests for flood risk prediction mutation hook.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '@/tests/mocks/server';
import { createMockPrediction } from '@/tests/mocks/handlers';
import { createWrapper } from '@/test/utils';
import { usePrediction } from '@/features/flooding/hooks/usePrediction';
import type { PredictionRequest } from '@/types';

describe('usePrediction', () => {
  const validPredictionData: PredictionRequest = {
    temperature: 298.15, // ~25°C in Kelvin
    humidity: 75,
    precipitation: 10,
    wind_speed: 12,
    pressure: 1013,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    server.resetHandlers();
  });

  it('should return initial state correctly', () => {
    const { result } = renderHook(() => usePrediction(), { wrapper: createWrapper() });

    expect(result.current.predict).toBeDefined();
    expect(result.current.predictAsync).toBeDefined();
    expect(result.current.isPending).toBe(false);
    expect(result.current.isSuccess).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.data).toBeUndefined();
    expect(result.current.error).toBeNull();
  });

  it('should make prediction successfully', async () => {
    const onSuccess = vi.fn();
    const { result } = renderHook(
      () => usePrediction({ onSuccess }),
      { wrapper: createWrapper() }
    );

    act(() => {
      result.current.predict(validPredictionData);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.isPending).toBe(false);
    expect(result.current.data).toBeDefined();
    expect(result.current.data?.prediction).toBeDefined();
    expect(result.current.data?.risk_level).toBeDefined();
    expect(result.current.data?.risk_label).toBeDefined();
    expect(result.current.data?.probability).toBeDefined();
    expect(onSuccess).toHaveBeenCalledTimes(1);
    const successCallArg = onSuccess.mock.calls[0][0];
    expect(successCallArg).toMatchObject({
      prediction: expect.any(Number),
      risk_level: expect.any(Number),
    });
  });

  it('should return Safe risk for low precipitation', async () => {
    const { result } = renderHook(() => usePrediction(), { wrapper: createWrapper() });

    act(() => {
      result.current.predict({
        ...validPredictionData,
        precipitation: 5,
        humidity: 50,
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.risk_level).toBe(0);
    expect(result.current.data?.risk_label).toBe('Safe');
  });

  it('should return Alert risk for moderate precipitation', async () => {
    const { result } = renderHook(() => usePrediction(), { wrapper: createWrapper() });

    act(() => {
      result.current.predict({
        ...validPredictionData,
        precipitation: 30,
        humidity: 75,
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.risk_level).toBe(1);
    expect(result.current.data?.risk_label).toBe('Alert');
  });

  it('should return Critical risk for high precipitation', async () => {
    const { result } = renderHook(() => usePrediction(), { wrapper: createWrapper() });

    act(() => {
      result.current.predict({
        ...validPredictionData,
        precipitation: 60,
        humidity: 95,
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.risk_level).toBe(2);
    expect(result.current.data?.risk_label).toBe('Critical');
  });

  it('should handle prediction error', async () => {
    server.use(
      http.post('*/api/v1/predict/predict', () => {
        return HttpResponse.json(
          { code: 'PREDICTION_FAILED', message: 'Model unavailable' },
          { status: 500 }
        );
      })
    );

    const onError = vi.fn();
    const { result } = renderHook(
      () => usePrediction({ onError }),
      { wrapper: createWrapper() }
    );

    act(() => {
      result.current.predict(validPredictionData);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeDefined();
    expect(onError).toHaveBeenCalled();
  });

  it('should handle network error', async () => {
    server.use(
      http.post('*/api/v1/predict/predict', () => {
        return HttpResponse.error();
      })
    );

    const { result } = renderHook(() => usePrediction(), { wrapper: createWrapper() });

    act(() => {
      result.current.predict(validPredictionData);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeDefined();
  });

  it('should reset mutation state', async () => {
    const { result } = renderHook(() => usePrediction(), { wrapper: createWrapper() });

    act(() => {
      result.current.predict(validPredictionData);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeDefined();

    act(() => {
      result.current.reset();
    });

    await waitFor(() => {
      expect(result.current.data).toBeUndefined();
    });
    expect(result.current.isSuccess).toBe(false);
    expect(result.current.isPending).toBe(false);
  });

  it('should support predictAsync for promise-based usage', async () => {
    const { result } = renderHook(() => usePrediction(), { wrapper: createWrapper() });

    let predictionResult: Awaited<ReturnType<typeof result.current.predictAsync>> | undefined;
    await act(async () => {
      predictionResult = await result.current.predictAsync(validPredictionData);
    });

    expect(predictionResult).toBeDefined();
    expect(predictionResult?.prediction).toBeDefined();
    expect(predictionResult?.risk_level).toBeDefined();
  });

  it('should handle optional pressure parameter', async () => {
    const { result } = renderHook(() => usePrediction(), { wrapper: createWrapper() });

    const dataWithoutPressure: PredictionRequest = {
      temperature: 298.15,
      humidity: 75,
      precipitation: 10,
      wind_speed: 12,
    };

    act(() => {
      result.current.predict(dataWithoutPressure);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeDefined();
  });
});
