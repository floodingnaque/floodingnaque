/**
 * PredictionForm Component
 *
 * Form for inputting weather parameters for flood risk prediction.
 * Supports two modes:
 *   1. Manual — user enters weather parameters directly
 *   2. Location — user shares GPS coordinates, backend fetches weather
 *
 * Uses react-hook-form with zod validation for manual mode.
 * Uses HTML5 Geolocation API for location mode.
 * Temperature is displayed in Celsius but converted to Kelvin for API.
 */

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  AlertCircle,
  Loader2,
  CloudRain,
  MapPin,
  LocateFixed,
  Keyboard,
} from 'lucide-react';

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
import { useLocationPrediction } from '../hooks/useLocationPrediction';
import { useGeolocation } from '@/hooks/useGeolocation';
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

/** Input mode: manual weather parameters or GPS location */
type InputMode = 'manual' | 'location';

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
 * PredictionForm renders a form for flood risk prediction.
 * Supports manual weather input and GPS-based location prediction.
 */
export function PredictionForm({ onSuccess }: PredictionFormProps) {
  const [mode, setMode] = useState<InputMode>('manual');

  // Manual prediction hook
  const {
    predict,
    isPending: isManualPending,
    isError: isManualError,
    error: manualError,
  } = usePrediction({ onSuccess });

  // Location prediction hook
  const {
    predictByLocation,
    isPending: isLocationPending,
    isError: isLocationError,
    error: locationError,
  } = useLocationPrediction({ onSuccess });

  // Geolocation hook
  const {
    coordinates,
    isLocating,
    error: geoError,
    isSupported: isGeoSupported,
    requestLocation,
  } = useGeolocation();

  const isPending = isManualPending || isLocationPending || isLocating;

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
    const requestData = {
      temperature: celsiusToKelvin(data.temperature),
      humidity: data.humidity,
      precipitation: data.precipitation,
      wind_speed: data.wind_speed,
      pressure: data.pressure ?? undefined,
    };
    predict(requestData);
  };

  /**
   * Handle "Share Location" → get GPS → send to backend
   */
  const handleLocationPredict = () => {
    if (coordinates) {
      // Coordinates already available — submit immediately
      predictByLocation({
        latitude: coordinates.latitude,
        longitude: coordinates.longitude,
      });
    } else {
      // Need to request location first, then submit on success
      // We request location; user clicks again once coordinates arrive
      requestLocation();
    }
  };

  // Error messages
  const manualErrorMessage =
    isManualError && manualError
      ? manualError.message || 'Prediction failed. Please try again.'
      : null;

  const locationErrorMessage =
    isLocationError && locationError
      ? locationError.message || 'Location prediction failed. Please try again.'
      : null;

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader className="space-y-1">
        <div className="flex items-center gap-2">
          <CloudRain className="h-6 w-6 text-blue-600" />
          <CardTitle className="text-2xl font-bold">
            Flood Risk Prediction
          </CardTitle>
        </div>
        <CardDescription>
          Choose how to provide weather data for flood risk assessment.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Mode Toggle */}
        <div className="flex rounded-lg border p-1 gap-1">
          <button
            type="button"
            onClick={() => setMode('manual')}
            className={`flex-1 flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              mode === 'manual'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <Keyboard className="h-4 w-4" />
            Manual Input
          </button>
          <button
            type="button"
            onClick={() => setMode('location')}
            className={`flex-1 flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              mode === 'location'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <MapPin className="h-4 w-4" />
            Share Location
          </button>
        </div>

        {/* ===== MANUAL MODE ===== */}
        {mode === 'manual' && (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {manualErrorMessage && (
              <Alert variant="destructive" role="alert" aria-live="assertive">
                <AlertCircle className="h-4 w-4" aria-hidden="true" />
                <AlertDescription>{manualErrorMessage}</AlertDescription>
              </Alert>
            )}

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
                    aria-describedby={
                      errors[field.name]
                        ? `${field.name}-error`
                        : `${field.name}-helper`
                    }
                  />
                  {errors[field.name] ? (
                    <p
                      id={`${field.name}-error`}
                      className="text-sm text-destructive"
                      role="alert"
                    >
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

            <Button
              type="submit"
              className="w-full"
              size="lg"
              disabled={isPending}
            >
              {isManualPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                'Predict Flood Risk'
              )}
            </Button>
          </form>
        )}

        {/* ===== LOCATION MODE ===== */}
        {mode === 'location' && (
          <div className="space-y-6">
            {/* Error alerts */}
            {geoError && (
              <Alert variant="destructive" role="alert" aria-live="assertive">
                <AlertCircle className="h-4 w-4" aria-hidden="true" />
                <AlertDescription>{geoError}</AlertDescription>
              </Alert>
            )}
            {locationErrorMessage && (
              <Alert variant="destructive" role="alert" aria-live="assertive">
                <AlertCircle className="h-4 w-4" aria-hidden="true" />
                <AlertDescription>{locationErrorMessage}</AlertDescription>
              </Alert>
            )}

            {/* Location status */}
            {coordinates && (
              <div className="rounded-lg border bg-muted/50 p-4 space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <LocateFixed className="h-4 w-4 text-green-600" />
                  Location acquired
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm text-muted-foreground">
                  <div>
                    <span className="font-medium text-foreground">Latitude:</span>{' '}
                    {coordinates.latitude.toFixed(6)}
                  </div>
                  <div>
                    <span className="font-medium text-foreground">Longitude:</span>{' '}
                    {coordinates.longitude.toFixed(6)}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Accuracy: ~{Math.round(coordinates.accuracy)}m
                </p>
              </div>
            )}

            {/* Geolocation not supported */}
            {!isGeoSupported && (
              <Alert role="alert">
                <AlertCircle className="h-4 w-4" aria-hidden="true" />
                <AlertDescription>
                  Geolocation is not supported by your browser. Please use
                  manual input instead.
                </AlertDescription>
              </Alert>
            )}

            {/* Action buttons */}
            <div className="space-y-3">
              {!coordinates ? (
                <Button
                  type="button"
                  className="w-full"
                  size="lg"
                  variant="outline"
                  disabled={!isGeoSupported || isPending}
                  onClick={requestLocation}
                >
                  {isLocating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Detecting location...
                    </>
                  ) : (
                    <>
                      <MapPin className="mr-2 h-4 w-4" />
                      Share My Location
                    </>
                  )}
                </Button>
              ) : (
                <Button
                  type="button"
                  className="w-full"
                  size="lg"
                  disabled={isPending}
                  onClick={handleLocationPredict}
                >
                  {isLocationPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Fetching weather &amp; predicting...
                    </>
                  ) : (
                    <>
                      <LocateFixed className="mr-2 h-4 w-4" />
                      Predict Flood Risk for My Location
                    </>
                  )}
                </Button>
              )}
            </div>

            {/* Privacy consent text */}
            <p className="text-xs text-muted-foreground text-center leading-relaxed">
              By sharing your location, you consent to its use for flood-risk
              prediction. Your coordinates are sent to our server to fetch
              real-time weather data and are not stored or shared with third
              parties.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default PredictionForm;
