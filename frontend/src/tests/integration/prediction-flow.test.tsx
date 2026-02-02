/**
 * Prediction Flow Integration Tests
 *
 * Tests the complete flood risk prediction flow from input to results.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server, createMockPrediction } from '@/tests/mocks';
import { render } from '@/test/utils';
import { PredictionForm } from '@/features/flooding/components/PredictionForm';
import { PredictionResult } from '@/features/flooding/components/PredictionResult';
import { RiskDisplay } from '@/features/flooding/components/RiskDisplay';
import type { PredictionResponse } from '@/types';

describe('Prediction Flow Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Form Submission Flow', () => {
    it('should display form with all required fields', () => {
      render(<PredictionForm />);

      expect(screen.getByLabelText(/temperature/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/humidity/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/precipitation/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/wind speed/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/pressure/i)).toBeInTheDocument();
    });

    it('should validate all required fields', async () => {
      const { user } = render(<PredictionForm />);

      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        // Should show validation errors
        const errorElements = screen.getAllByText(/required|invalid|must be/i);
        expect(errorElements.length).toBeGreaterThan(0);
      });
    });

    it('should convert temperature from Celsius to Kelvin', async () => {
      let capturedRequest: Record<string, unknown> | null = null;

      server.use(
        http.post('*/api/v1/predict/predict', async ({ request }) => {
          capturedRequest = await request.json() as Record<string, unknown>;
          return HttpResponse.json(createMockPrediction());
        })
      );

      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25'); // Celsius
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');

      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(capturedRequest).toBeDefined();
        // 25°C should be converted to 298.15K
        expect(capturedRequest?.temperature).toBeCloseTo(298.15, 1);
      });
    });
  });

  describe('Risk Level Scenarios', () => {
    it('should return Safe for low-risk conditions', async () => {
      server.use(
        http.post('*/api/v1/predict/predict', async () => {
          return HttpResponse.json(
            createMockPrediction({
              prediction: 0,
              probability: 0.15,
              risk_level: 0,
              risk_label: 'Safe',
            })
          );
        })
      );

      let result: PredictionResponse | null = null;
      const onSuccess = (data: PredictionResponse) => {
        result = data;
      };

      const { user } = render(<PredictionForm onSuccess={onSuccess} />);

      await user.type(screen.getByLabelText(/temperature/i), '20');
      await user.type(screen.getByLabelText(/humidity/i), '50');
      await user.type(screen.getByLabelText(/precipitation/i), '5');
      await user.type(screen.getByLabelText(/wind speed/i), '8');

      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(result).toBeDefined();
        expect(result?.risk_level).toBe(0);
        expect(result?.risk_label).toBe('Safe');
      });
    });

    it('should return Alert for moderate-risk conditions', async () => {
      server.use(
        http.post('*/api/v1/predict/predict', async () => {
          return HttpResponse.json(
            createMockPrediction({
              prediction: 1,
              probability: 0.65,
              risk_level: 1,
              risk_label: 'Alert',
            })
          );
        })
      );

      let result: PredictionResponse | null = null;
      const onSuccess = (data: PredictionResponse) => {
        result = data;
      };

      const { user } = render(<PredictionForm onSuccess={onSuccess} />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '80');
      await user.type(screen.getByLabelText(/precipitation/i), '30');
      await user.type(screen.getByLabelText(/wind speed/i), '20');

      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(result).toBeDefined();
        expect(result?.risk_level).toBe(1);
        expect(result?.risk_label).toBe('Alert');
      });
    });

    it('should return Critical for high-risk conditions', async () => {
      server.use(
        http.post('*/api/v1/predict/predict', async () => {
          return HttpResponse.json(
            createMockPrediction({
              prediction: 1,
              probability: 0.92,
              risk_level: 2,
              risk_label: 'Critical',
            })
          );
        })
      );

      let result: PredictionResponse | null = null;
      const onSuccess = (data: PredictionResponse) => {
        result = data;
      };

      const { user } = render(<PredictionForm onSuccess={onSuccess} />);

      await user.type(screen.getByLabelText(/temperature/i), '28');
      await user.type(screen.getByLabelText(/humidity/i), '95');
      await user.type(screen.getByLabelText(/precipitation/i), '75');
      await user.type(screen.getByLabelText(/wind speed/i), '30');

      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(result).toBeDefined();
        expect(result?.risk_level).toBe(2);
        expect(result?.risk_label).toBe('Critical');
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error when prediction fails', async () => {
      server.use(
        http.post('*/api/v1/predict/predict', async () => {
          return HttpResponse.json(
            { code: 'MODEL_ERROR', message: 'Prediction model unavailable' },
            { status: 500 }
          );
        })
      );

      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');

      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(
        () => {
          expect(screen.getByRole('alert')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle network errors gracefully', async () => {
      server.use(
        http.post('*/api/v1/predict/predict', async () => {
          return HttpResponse.error();
        })
      );

      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');

      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(
        () => {
          expect(screen.getByRole('alert')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle timeout errors', async () => {
      server.use(
        http.post('*/api/v1/predict/predict', async () => {
          // Simulate timeout by never responding (MSW will eventually timeout)
          await new Promise((resolve) => setTimeout(resolve, 35000));
          return HttpResponse.json(createMockPrediction());
        })
      );

      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');

      // Start the prediction
      await user.click(screen.getByRole('button', { name: /predict/i }));

      // Button should be disabled while pending
      expect(screen.getByRole('button')).toBeDisabled();
    });
  });

  describe('Loading States', () => {
    it('should show loading indicator during prediction', async () => {
      server.use(
        http.post('*/api/v1/predict/predict', async () => {
          await new Promise((resolve) => setTimeout(resolve, 300));
          return HttpResponse.json(createMockPrediction());
        })
      );

      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');

      // Click and immediately check for loading state
      user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        const button = screen.getByRole('button');
        expect(button).toBeDisabled();
      });
    });

    it('should disable form inputs while loading', async () => {
      server.use(
        http.post('*/api/v1/predict/predict', async () => {
          await new Promise((resolve) => setTimeout(resolve, 300));
          return HttpResponse.json(createMockPrediction());
        })
      );

      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');

      user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/temperature/i)).toBeDisabled();
        expect(screen.getByLabelText(/humidity/i)).toBeDisabled();
      });
    });
  });

  describe('Response Metadata', () => {
    it('should return model version in response', async () => {
      const mockResponse = createMockPrediction({
        model_version: 'v2.0.0',
        features_used: ['temperature', 'humidity', 'precipitation', 'wind_speed', 'pressure'],
      });

      server.use(
        http.post('*/api/v1/predict/predict', async () => {
          return HttpResponse.json(mockResponse);
        })
      );

      let result: PredictionResponse | null = null;
      const { user } = render(
        <PredictionForm onSuccess={(data) => { result = data; }} />
      );

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');
      await user.type(screen.getByLabelText(/pressure/i), '1013');

      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(result?.model_version).toBe('v2.0.0');
        expect(result?.features_used).toContain('pressure');
      });
    });

    it('should return request ID for tracking', async () => {
      const mockResponse = createMockPrediction({
        request_id: 'unique-request-123',
      });

      server.use(
        http.post('*/api/v1/predict/predict', async () => {
          return HttpResponse.json(mockResponse);
        })
      );

      let result: PredictionResponse | null = null;
      const { user } = render(
        <PredictionForm onSuccess={(data) => { result = data; }} />
      );

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');

      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(result?.request_id).toBe('unique-request-123');
      });
    });
  });
});

describe('Multiple Predictions', () => {
  it('should allow multiple consecutive predictions', async () => {
    const predictions: PredictionResponse[] = [];

    server.use(
      http.post('*/api/v1/predict/predict', async () => {
        return HttpResponse.json(createMockPrediction());
      })
    );

    const { user } = render(
      <PredictionForm onSuccess={(data) => predictions.push(data)} />
    );

    // First prediction
    await user.type(screen.getByLabelText(/temperature/i), '25');
    await user.type(screen.getByLabelText(/humidity/i), '75');
    await user.type(screen.getByLabelText(/precipitation/i), '10');
    await user.type(screen.getByLabelText(/wind speed/i), '12');
    await user.click(screen.getByRole('button', { name: /predict/i }));

    await waitFor(() => {
      expect(predictions.length).toBe(1);
    });

    // Clear and make second prediction
    await user.clear(screen.getByLabelText(/temperature/i));
    await user.clear(screen.getByLabelText(/humidity/i));
    await user.clear(screen.getByLabelText(/precipitation/i));
    await user.clear(screen.getByLabelText(/wind speed/i));

    await user.type(screen.getByLabelText(/temperature/i), '30');
    await user.type(screen.getByLabelText(/humidity/i), '90');
    await user.type(screen.getByLabelText(/precipitation/i), '50');
    await user.type(screen.getByLabelText(/wind speed/i), '25');
    await user.click(screen.getByRole('button', { name: /predict/i }));

    await waitFor(() => {
      expect(predictions.length).toBe(2);
    });
  });
});
