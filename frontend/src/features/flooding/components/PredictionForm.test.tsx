/**
 * PredictionForm Component Tests
 *
 * Tests for the PredictionForm component with weather parameter input.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import { PredictionForm } from '@/features/flooding/components/PredictionForm';
import type { PredictionResponse } from '@/types';

// Mock usePrediction hook
const mockPredict = vi.fn();
const mockUsePrediction: {
  predict: typeof mockPredict;
  isPending: boolean;
  isError: boolean;
  error: { message?: string } | null;
} = {
  predict: mockPredict,
  isPending: false,
  isError: false,
  error: null,
};

vi.mock('../hooks/usePrediction', () => ({
  usePrediction: (options?: { onSuccess?: (data: PredictionResponse) => void }) => ({
    ...mockUsePrediction,
    predict: (data: unknown) => {
      mockPredict(data);
      if (options?.onSuccess) {
        options.onSuccess({
          prediction: 1,
          probability: 0.75,
          risk_level: 1,
          risk_label: 'Alert',
          confidence: 0.85,
          model_version: 'v1.0.0',
          features_used: ['temperature', 'humidity', 'precipitation', 'wind_speed'],
          timestamp: new Date().toISOString(),
          request_id: 'test-id',
        });
      }
    },
  }),
}));

// Mock temperature utils
vi.mock('../utils/temperature', () => ({
  celsiusToKelvin: (celsius: number) => celsius + 273.15,
}));

describe('PredictionForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePrediction.isPending = false;
    mockUsePrediction.isError = false;
    mockUsePrediction.error = null;
  });

  describe('Rendering', () => {
    it('should render form title', () => {
      render(<PredictionForm />);

      expect(screen.getByText('Weather Parameters')).toBeInTheDocument();
    });

    it('should render temperature input', () => {
      render(<PredictionForm />);

      expect(screen.getByLabelText(/temperature/i)).toBeInTheDocument();
    });

    it('should render humidity input', () => {
      render(<PredictionForm />);

      expect(screen.getByLabelText(/humidity/i)).toBeInTheDocument();
    });

    it('should render precipitation input', () => {
      render(<PredictionForm />);

      expect(screen.getByLabelText(/precipitation/i)).toBeInTheDocument();
    });

    it('should render wind speed input', () => {
      render(<PredictionForm />);

      expect(screen.getByLabelText(/wind speed/i)).toBeInTheDocument();
    });

    it('should render optional pressure input', () => {
      render(<PredictionForm />);

      expect(screen.getByLabelText(/pressure/i)).toBeInTheDocument();
    });

    it('should render submit button', () => {
      render(<PredictionForm />);

      expect(screen.getByRole('button', { name: /predict flood risk/i })).toBeInTheDocument();
    });

    it('should render helper text for inputs', () => {
      render(<PredictionForm />);

      expect(screen.getByText(/temperature in degrees celsius/i)).toBeInTheDocument();
      expect(screen.getByText(/relative humidity as percentage/i)).toBeInTheDocument();
      expect(screen.getByText(/rainfall amount in millimeters/i)).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('should show error for temperature out of range', async () => {
      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '-60');
      await user.type(screen.getByLabelText(/humidity/i), '50');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '10');
      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(screen.getByText(/temperature must be at least -50/i)).toBeInTheDocument();
      });
    });

    it('should show error for humidity out of range', async () => {
      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '150');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '10');
      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(screen.getByText(/humidity must be at most 100/i)).toBeInTheDocument();
      });
    });

    it('should show error for negative precipitation', async () => {
      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '50');
      await user.type(screen.getByLabelText(/precipitation/i), '-5');
      await user.type(screen.getByLabelText(/wind speed/i), '10');
      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(screen.getByText(/precipitation cannot be negative/i)).toBeInTheDocument();
      });
    });

    it('should show error for negative wind speed', async () => {
      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '50');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '-5');
      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(screen.getByText(/wind speed cannot be negative/i)).toBeInTheDocument();
      });
    });

    it('should allow optional pressure field', async () => {
      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '50');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '10');
      // Don't fill pressure
      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(mockPredict).toHaveBeenCalled();
      });
    });
  });

  describe('Form Submission', () => {
    it('should call predict with converted temperature', async () => {
      const onSuccess = vi.fn();
      const { user } = render(<PredictionForm onSuccess={onSuccess} />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');
      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(mockPredict).toHaveBeenCalledWith(
          expect.objectContaining({
            temperature: 298.15, // 25 + 273.15
            humidity: 75,
            precipitation: 10,
            wind_speed: 12,
          })
        );
      });
    });

    it('should call onSuccess callback when prediction succeeds', async () => {
      const onSuccess = vi.fn();
      const { user } = render(<PredictionForm onSuccess={onSuccess} />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');
      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledWith(
          expect.objectContaining({
            prediction: expect.any(Number),
            risk_level: expect.any(Number),
          })
        );
      });
    });

    it('should include pressure when provided', async () => {
      const { user } = render(<PredictionForm />);

      await user.type(screen.getByLabelText(/temperature/i), '25');
      await user.type(screen.getByLabelText(/humidity/i), '75');
      await user.type(screen.getByLabelText(/precipitation/i), '10');
      await user.type(screen.getByLabelText(/wind speed/i), '12');
      await user.type(screen.getByLabelText(/pressure/i), '1013');
      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(mockPredict).toHaveBeenCalledWith(
          expect.objectContaining({
            pressure: 1013,
          })
        );
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading state when predicting', () => {
      mockUsePrediction.isPending = true;
      render(<PredictionForm />);

      expect(screen.getByRole('button', { name: /analyzing/i })).toBeInTheDocument();
      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('should disable inputs when predicting', () => {
      mockUsePrediction.isPending = true;
      render(<PredictionForm />);

      expect(screen.getByLabelText(/temperature/i)).toBeDisabled();
      expect(screen.getByLabelText(/humidity/i)).toBeDisabled();
      expect(screen.getByLabelText(/precipitation/i)).toBeDisabled();
      expect(screen.getByLabelText(/wind speed/i)).toBeDisabled();
      expect(screen.getByLabelText(/pressure/i)).toBeDisabled();
    });
  });

  describe('Error Display', () => {
    it('should display prediction error message', () => {
      mockUsePrediction.isError = true;
      mockUsePrediction.error = { message: 'Model unavailable' };
      render(<PredictionForm />);

      expect(screen.getByText('Model unavailable')).toBeInTheDocument();
    });

    it('should display default error message if none provided', () => {
      mockUsePrediction.isError = true;
      mockUsePrediction.error = {};
      render(<PredictionForm />);

      expect(screen.getByText(/prediction failed/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have aria-invalid on invalid inputs', async () => {
      const { user } = render(<PredictionForm />);

      await user.click(screen.getByRole('button', { name: /predict/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/temperature/i)).toHaveAttribute('aria-invalid', 'true');
      });
    });

    it('should have helper text connected via aria-describedby', () => {
      render(<PredictionForm />);

      expect(screen.getByLabelText(/temperature/i)).toHaveAttribute('aria-describedby', 'temperature-helper');
    });
  });
});
