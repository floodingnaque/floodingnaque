/**
 * PredictionForm Component - Web 3.0 Edition
 *
 * Modern flood risk prediction form with glassmorphism cards,
 * animated mode toggle, icon-enhanced fields with unit badges,
 * and smooth micro-interactions.
 *
 * Supports two modes:
 *   1. Manual - user enters weather parameters directly
 *   2. Location - user shares GPS coordinates, backend fetches weather
 *
 * Uses react-hook-form with zod validation for manual mode.
 * Uses HTML5 Geolocation API for location mode.
 * Temperature is displayed in Celsius but converted to Kelvin for API.
 */

import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  CloudRain,
  CloudRainWind,
  CloudSun,
  Droplets,
  Gauge,
  Info,
  Keyboard,
  Loader2,
  LocateFixed,
  MapPin,
  Navigation,
  Shield,
  Thermometer,
  Wind,
  Zap,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { GlassCard } from "@/components/ui/glass-card";
import { Label } from "@/components/ui/label";

import { useGeolocation } from "@/hooks/useGeolocation";
import type { PredictionResponse } from "@/types";
import type { LucideIcon } from "lucide-react";
import { useLocationPrediction } from "../hooks/useLocationPrediction";
import { usePrediction } from "../hooks/usePrediction";
import { celsiusToKelvin } from "../utils/temperature";

/**
 * Helper to validate required numbers (handles NaN from empty inputs)
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
 */
const predictionSchema = z.object({
  temperature: requiredNumber("Temperature")
    .min(-50, "Temperature must be at least -50°C")
    .max(60, "Temperature must be at most 60°C"),
  humidity: requiredNumber("Humidity")
    .min(0, "Humidity must be at least 0%")
    .max(100, "Humidity must be at most 100%"),
  precipitation: requiredNumber("Precipitation").min(
    0,
    "Precipitation cannot be negative",
  ),
  wind_speed: requiredNumber("Wind speed").min(
    0,
    "Wind speed cannot be negative",
  ),
  pressure: z
    .number()
    .min(900, "Pressure must be at least 900 hPa")
    .max(1100, "Pressure must be at most 1100 hPa")
    .optional()
    .nullable()
    .or(z.nan().transform(() => undefined)),
});

type PredictionFormData = {
  temperature: number;
  humidity: number;
  precipitation: number;
  wind_speed: number;
  pressure?: number | null;
};

type InputMode = "manual" | "location";

interface PredictionFormProps {
  onSuccess?: (result: PredictionResponse) => void;
}

/**
 * Field configuration with icons and units for enhanced rendering
 */
interface FieldConfig {
  name: keyof PredictionFormData;
  label: string;
  placeholder: string;
  helper: string;
  step?: string;
  icon: LucideIcon;
  unit: string;
}

const fields: FieldConfig[] = [
  {
    name: "temperature",
    label: "Temperature",
    placeholder: "e.g., 25",
    helper: "Temperature in degrees Celsius (°C)",
    icon: Thermometer,
    unit: "°C",
  },
  {
    name: "humidity",
    label: "Humidity",
    placeholder: "e.g., 80",
    helper: "Relative humidity as percentage (0-100%)",
    icon: Droplets,
    unit: "%",
  },
  {
    name: "precipitation",
    label: "Precipitation",
    placeholder: "e.g., 50",
    helper: "Rainfall amount in millimeters (mm)",
    step: "0.1",
    icon: CloudRainWind,
    unit: "mm",
  },
  {
    name: "wind_speed",
    label: "Wind Speed",
    placeholder: "e.g., 15",
    helper: "Wind speed in meters per second (m/s)",
    step: "0.1",
    icon: Wind,
    unit: "m/s",
  },
  {
    name: "pressure",
    label: "Pressure (Optional)",
    placeholder: "e.g., 1013",
    helper: "Atmospheric pressure in hectopascals (hPa)",
    icon: Gauge,
    unit: "hPa",
  },
];

/** Animation variants */
const containerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: "easeOut" as const },
  },
} as const;

const modeTransition = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.25 },
};

/**
 * PredictionForm renders a modern form for flood risk prediction.
 */
export function PredictionForm({ onSuccess }: PredictionFormProps) {
  const [mode, setMode] = useState<InputMode>("manual");

  const {
    predict,
    isPending: isManualPending,
    isError: isManualError,
    error: manualError,
  } = usePrediction({ onSuccess });

  const {
    predictByLocation,
    isPending: isLocationPending,
    isError: isLocationError,
    error: locationError,
  } = useLocationPrediction({ onSuccess });

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
    setValue,
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

  /** Weather presets for quick-fill */
  const applyPreset = (preset: "clear" | "rainy" | "storm") => {
    const presets = {
      clear: {
        temperature: 32,
        humidity: 65,
        precipitation: 0,
        wind_speed: 3,
        pressure: 1013,
      },
      rainy: {
        temperature: 27,
        humidity: 88,
        precipitation: 25,
        wind_speed: 8,
        pressure: 1005,
      },
      storm: {
        temperature: 24,
        humidity: 95,
        precipitation: 80,
        wind_speed: 22,
        pressure: 990,
      },
    };
    const data = presets[preset];
    (Object.keys(data) as (keyof typeof data)[]).forEach((key) => {
      setValue(key, data[key], { shouldValidate: true });
    });
  };

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

  const handleLocationPredict = () => {
    if (coordinates) {
      predictByLocation({
        latitude: coordinates.latitude,
        longitude: coordinates.longitude,
      });
    } else {
      requestLocation();
    }
  };

  const manualErrorMessage =
    isManualError && manualError
      ? manualError.message || "Prediction failed. Please try again."
      : null;

  const locationErrorMessage =
    isLocationError && locationError
      ? locationError.message || "Location prediction failed. Please try again."
      : null;

  return (
    <GlassCard
      intensity="medium"
      className="w-full max-w-2xl mx-auto overflow-hidden"
    >
      {/* Decorative gradient accent */}
      <div className="h-1 w-full bg-linear-to-r from-primary/80 via-primary to-primary/80" />

      <div className="p-4 sm:p-6 space-y-1.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <CloudRain className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight">
              Flood Risk Prediction
            </h2>
            <p className="text-sm text-muted-foreground">
              Choose how to provide weather data for assessment.
            </p>
          </div>
        </div>
      </div>

      <div className="px-6 pb-6 space-y-6">
        {/* Mode Toggle - Segmented Control */}
        <div className="relative flex rounded-xl border border-border/50 bg-muted/30 p-1 gap-1">
          <button
            type="button"
            onClick={() => setMode("manual")}
            className={`relative flex-1 flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-300 ${
              mode === "manual"
                ? "bg-background text-foreground shadow-md"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Keyboard className="h-4 w-4" />
            Manual Input
          </button>
          <button
            type="button"
            onClick={() => setMode("location")}
            className={`relative flex-1 flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-300 ${
              mode === "location"
                ? "bg-background text-foreground shadow-md"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <MapPin className="h-4 w-4" />
            Share Location
          </button>
        </div>

        {/* ===== MANUAL MODE ===== */}
        <AnimatePresence mode="wait">
          {mode === "manual" && (
            <motion.form
              key="manual"
              onSubmit={handleSubmit(onSubmit)}
              className="space-y-6"
              {...modeTransition}
            >
              <AnimatePresence>
                {manualErrorMessage && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25 }}
                  >
                    <Alert
                      variant="destructive"
                      role="alert"
                      aria-live="assertive"
                      className="border-destructive/30 bg-destructive/10"
                    >
                      <AlertCircle className="h-4 w-4" aria-hidden="true" />
                      <AlertDescription>{manualErrorMessage}</AlertDescription>
                    </Alert>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Intro guidance */}
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="rounded-xl border border-primary/15 bg-primary/5 p-4 flex gap-3"
              >
                <Info className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Enter current weather conditions for your area. Our AI model
                  trained on 3,700+ Parañaque flood records will assess the risk
                  level.
                </p>
              </motion.div>

              {/* Quick-fill presets */}
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.3 }}
                className="space-y-2"
              >
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Quick Fill
                </p>
                <div className="flex flex-wrap gap-2">
                  {[
                    {
                      key: "clear" as const,
                      label: "Clear Day",
                      icon: CloudSun,
                      desc: "32°C · 65% · 0 mm",
                    },
                    {
                      key: "rainy" as const,
                      label: "Rainy Day",
                      icon: CloudRainWind,
                      desc: "27°C · 88% · 25 mm",
                    },
                    {
                      key: "storm" as const,
                      label: "Storm",
                      icon: Zap,
                      desc: "24°C · 95% · 80 mm",
                    },
                  ].map((preset) => (
                    <button
                      key={preset.key}
                      type="button"
                      disabled={isPending}
                      onClick={() => applyPreset(preset.key)}
                      className="group flex items-center gap-2 rounded-lg border border-border/50 bg-background/60 px-3 py-2 text-sm transition-all hover:border-primary/30 hover:bg-primary/5 disabled:opacity-50 disabled:pointer-events-none"
                    >
                      <preset.icon className="h-4 w-4 text-primary/70 group-hover:text-primary transition-colors" />
                      <span className="font-medium">{preset.label}</span>
                      <span className="text-[11px] text-muted-foreground/60 hidden sm:inline">
                        {preset.desc}
                      </span>
                    </button>
                  ))}
                </div>
              </motion.div>

              <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="show"
                className="grid grid-cols-1 md:grid-cols-2 gap-5"
              >
                {fields.map((field) => (
                  <motion.div
                    key={field.name}
                    variants={itemVariants}
                    className={field.name === "pressure" ? "md:col-span-2" : ""}
                  >
                    <FormField
                      id={field.name}
                      label={field.label}
                      icon={field.icon}
                      type="number"
                      step={field.step || "any"}
                      placeholder={field.placeholder}
                      disabled={isPending}
                      error={errors[field.name]?.message}
                      helperText={field.helper}
                      {...register(field.name, { valueAsNumber: true })}
                      trailing={
                        <span className="text-xs font-medium text-muted-foreground/60 select-none">
                          {field.unit}
                        </span>
                      }
                    />
                  </motion.div>
                ))}
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.3 }}
              >
                <Button
                  type="submit"
                  className="w-full h-12 rounded-xl bg-linear-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all duration-300 text-base"
                  size="lg"
                  disabled={isPending}
                >
                  {isManualPending ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Analyzing Weather Data...
                    </>
                  ) : (
                    <>
                      <Shield className="mr-2 h-5 w-5" />
                      Predict Flood Risk
                    </>
                  )}
                </Button>
              </motion.div>
            </motion.form>
          )}

          {/* ===== LOCATION MODE ===== */}
          {mode === "location" && (
            <motion.div
              key="location"
              className="space-y-6"
              {...modeTransition}
            >
              {/* Error alerts */}
              <AnimatePresence>
                {geoError && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    <Alert
                      variant="destructive"
                      role="alert"
                      aria-live="assertive"
                      className="border-destructive/30 bg-destructive/10"
                    >
                      <AlertCircle className="h-4 w-4" aria-hidden="true" />
                      <AlertDescription>{geoError}</AlertDescription>
                    </Alert>
                  </motion.div>
                )}
                {locationErrorMessage && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    <Alert
                      variant="destructive"
                      role="alert"
                      aria-live="assertive"
                      className="border-destructive/30 bg-destructive/10"
                    >
                      <AlertCircle className="h-4 w-4" aria-hidden="true" />
                      <AlertDescription>
                        {locationErrorMessage}
                      </AlertDescription>
                    </Alert>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Step indicator */}
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="flex items-center justify-between gap-2"
              >
                {[
                  {
                    step: 1,
                    label: "Share Location",
                    icon: MapPin,
                    done: !!coordinates,
                  },
                  {
                    step: 2,
                    label: "Fetch Weather",
                    icon: CloudRain,
                    done: false,
                  },
                  {
                    step: 3,
                    label: "Get Prediction",
                    icon: Shield,
                    done: false,
                  },
                ].map((s, i) => (
                  <div key={s.step} className="flex items-center gap-2 flex-1">
                    <div
                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                        s.done
                          ? "bg-primary text-primary-foreground"
                          : (!coordinates && s.step === 1) ||
                              (coordinates && s.step === 2)
                            ? "bg-primary/15 text-primary ring-2 ring-primary/30"
                            : "bg-muted text-muted-foreground"
                      }`}
                    >
                      <s.icon className="h-3.5 w-3.5" />
                    </div>
                    <span
                      className={`text-xs font-medium hidden sm:inline ${
                        s.done
                          ? "text-primary"
                          : (!coordinates && s.step === 1) ||
                              (coordinates && s.step === 2)
                            ? "text-foreground"
                            : "text-muted-foreground"
                      }`}
                    >
                      {s.label}
                    </span>
                    {i < 2 && (
                      <div
                        className={`flex-1 h-px transition-colors ${
                          s.done ? "bg-primary" : "bg-border/50"
                        }`}
                      />
                    )}
                  </div>
                ))}
              </motion.div>

              {/* How it works - shown before location is acquired */}
              {!coordinates && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1, duration: 0.3 }}
                  className="rounded-xl border border-primary/15 bg-primary/5 p-4 space-y-3"
                >
                  <div className="flex items-center gap-2">
                    <Info className="h-4 w-4 text-primary" />
                    <p className="text-sm font-medium text-foreground">
                      How it works
                    </p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {[
                      {
                        icon: Navigation,
                        title: "GPS Coordinates",
                        desc: "We detect your precise location within Parañaque",
                      },
                      {
                        icon: CloudRain,
                        title: "Weather Data",
                        desc: "Real-time conditions are fetched from nearby stations",
                      },
                      {
                        icon: Shield,
                        title: "AI Prediction",
                        desc: "Our model analyzes all data to assess flood risk",
                      },
                    ].map((item) => (
                      <div
                        key={item.title}
                        className="flex flex-col items-center text-center gap-1.5 p-2"
                      >
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                          <item.icon className="h-4 w-4 text-primary" />
                        </div>
                        <p className="text-xs font-semibold">{item.title}</p>
                        <p className="text-[11px] text-muted-foreground leading-snug">
                          {item.desc}
                        </p>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Location status card */}
              <AnimatePresence>
                {coordinates && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm font-medium text-primary">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/15">
                          <LocateFixed className="h-3.5 w-3.5" />
                        </div>
                        Location Acquired
                      </div>
                      <span className="text-[11px] text-muted-foreground bg-muted/50 px-2 py-0.5 rounded-full">
                        ±{Math.round(coordinates.accuracy)}m accuracy
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-lg bg-background/60 border border-border/30 p-3">
                        <Label className="text-[11px] text-muted-foreground uppercase tracking-wider">
                          Latitude
                        </Label>
                        <p className="text-sm font-mono font-semibold mt-0.5">
                          {coordinates.latitude.toFixed(6)}°
                        </p>
                      </div>
                      <div className="rounded-lg bg-background/60 border border-border/30 p-3">
                        <Label className="text-[11px] text-muted-foreground uppercase tracking-wider">
                          Longitude
                        </Label>
                        <p className="text-sm font-mono font-semibold mt-0.5">
                          {coordinates.longitude.toFixed(6)}°
                        </p>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                      <Navigation className="h-3 w-3" />
                      Parañaque City, Metro Manila
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>

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
                    className="w-full h-12 rounded-xl bg-linear-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all duration-300 text-base"
                    size="lg"
                    disabled={!isGeoSupported || isPending}
                    onClick={requestLocation}
                  >
                    {isLocating ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Detecting your location...
                      </>
                    ) : (
                      <>
                        <MapPin className="mr-2 h-5 w-5" />
                        Share My Location
                      </>
                    )}
                  </Button>
                ) : (
                  <Button
                    type="button"
                    className="w-full h-12 rounded-xl bg-linear-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all duration-300 text-base"
                    size="lg"
                    disabled={isPending}
                    onClick={handleLocationPredict}
                  >
                    {isLocationPending ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Fetching weather &amp; predicting...
                      </>
                    ) : (
                      <>
                        <Shield className="mr-2 h-5 w-5" />
                        Predict Flood Risk for My Location
                      </>
                    )}
                  </Button>
                )}
              </div>

              {/* Privacy consent */}
              <div className="w-full h-px bg-linear-to-r from-transparent via-border/50 to-transparent" />
              <p className="text-xs text-muted-foreground text-center leading-relaxed">
                By sharing your location, you consent to its use for flood-risk
                prediction. Your coordinates are sent to our server to fetch
                real-time weather data and are not stored or shared with third
                parties.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </GlassCard>
  );
}

export default PredictionForm;
