/**
 * PredictionForm Component
 *
 * Form for inputting weather parameters for flood risk prediction.
 * Uses react-hook-form with zod validation.
 * Temperature is displayed in Celsius but converted to Kelvin for API.
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AlertCircle, Loader2, CloudRain } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

import { usePrediction } from '../hooks/usePrediction';
import { celsiusToKelvin } from '../utils/temperature';
import type { PredictionResponse } from '@/types';

/**
 * Helper to validate required numbers (handles NaN from empty inputs)
 * When using valueAsNumber: true, empty inputs return NaN instead of undefined
 */
const requiredNumber = (fieldName: string) =>
  z
    .number({
      error: `${fieldName} must be a valid number`,
    })
    .refine((val) => !Number.isNaN(val), {
      message: `${fieldName} is required`,
    });

/**
 * Form validation schema
 * All fields except pressure are required
 */
const predictionSchema = z.object({
  temperature: requiredNumber('Temperature')
    .min(-50, 'Temperature must be at least -50°C')
    .max(60, 'Temperature must be at most 60°C'),
  humidity: requiredNumber('Humidity')
    .min(0, 'Humidity must be at least 0%')
    .max(100, 'Humidity must be at most 100%'),
  precipitation: requiredNumber('Precipitation').min(
    0,
    'Precipitation cannot be negative'
  ),
  wind_speed: requiredNumber('Wind speed').min(
    0,
    'Wind speed cannot be negative'
  ),
  pressure: z
    .number()
    .min(900, 'Pressure must be at least 900 hPa')
    .max(1100, 'Pressure must be at most 1100 hPa')
    .optional()
    .nullable()
    .or(z.nan().transform(() => undefined)),
});

/**
 * Form data type for prediction form
 */
type PredictionFormData = {
  temperature: number;
  humidity: number;
  precipitation: number;
  wind_speed: number;
  pressure?: number | null;
};

/**
 * PredictionForm component props
 */
interface PredictionFormProps {
  /** Callback when prediction succeeds */
  onSuccess?: (result: PredictionResponse) => void;
}

/**
 * Field configuration for consistent rendering
 */
interface FieldConfig {
  name: keyof PredictionFormData;
  label: string;
  placeholder: string;
  helper: string;
  step?: string;
}

const fields: FieldConfig[] = [
  {
    name: 'temperature',
    label: 'Temperature',
    placeholder: 'e.g., 25',
    helper: 'Temperature in degrees Celsius (°C)',
  },
  {
    name: 'humidity',
    label: 'Humidity',
    placeholder: 'e.g., 80',
    helper: 'Relative humidity as percentage (0-100%)',
  },
  {
    name: 'precipitation',
    label: 'Precipitation',
    placeholder: 'e.g., 50',
    helper: 'Rainfall amount in millimeters (mm)',
    step: '0.1',
  },
  {
    name: 'wind_speed',
    label: 'Wind Speed',
    placeholder: 'e.g., 15',
    helper: 'Wind speed in meters per second (m/s)',
    step: '0.1',
  },
  {
    name: 'pressure',
    label: 'Pressure (Optional)',
    placeholder: 'e.g., 1013',
    helper: 'Atmospheric pressure in hectopascals (hPa)',
  },
];

/**
 * PredictionForm renders a form for flood risk prediction
 */
export function PredictionForm({ onSuccess }: PredictionFormProps) {
  const { predict, isPending, isError, error } = usePrediction({
    onSuccess,
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PredictionFormData>({
    resolver: zodResolver(predictionSchema),
    defaultValues: {
      temperature: undefined,
      humidity: undefined,
      precipitation: undefined,
      wind_speed: undefined,
      pressure: undefined,
    },
  });

  const onSubmit = (data: PredictionFormData) => {
    // Convert temperature from Celsius to Kelvin for API
    const requestData = {
      temperature: celsiusToKelvin(data.temperature),
      humidity: data.humidity,
      precipitation: data.precipitation,
      wind_speed: data.wind_speed,
      pressure: data.pressure ?? undefined,
    };

    predict(requestData);
  };

  // Extract error message
  const errorMessage = isError && error
    ? error.message || 'Prediction failed. Please try again.'
    : null;

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader className="space-y-1">
        <div className="flex items-center gap-2">
          <CloudRain className="h-6 w-6 text-blue-600" />
          <CardTitle className="text-2xl font-bold">
            Weather Parameters
          </CardTitle>
        </div>
        <CardDescription>
          Enter the current weather conditions to predict flood risk.
          All fields except pressure are required.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* API Error Alert */}
          {errorMessage && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}

          {/* Form Fields - 2 column grid on desktop */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {fields.map((field) => (
              <div key={field.name} className="space-y-2">
                <Label htmlFor={field.name}>{field.label}</Label>
                <Input
                  id={field.name}
                  type="number"
                  step={field.step || 'any'}
                  placeholder={field.placeholder}
                  disabled={isPending}
                  {...register(field.name, { valueAsNumber: true })}
                  aria-invalid={!!errors[field.name]}
                  aria-describedby={`${field.name}-helper`}
                />
                {errors[field.name] ? (
                  <p className="text-sm text-destructive">
                    {errors[field.name]?.message}
                  </p>
                ) : (
                  <p
                    id={`${field.name}-helper`}
                    className="text-sm text-muted-foreground"
                  >
                    {field.helper}
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={isPending}
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              'Predict Flood Risk'
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default PredictionForm;
