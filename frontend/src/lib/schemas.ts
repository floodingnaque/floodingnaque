/**
 * Zod Schemas for API Response Validation
 *
 * Runtime validation layer for backend responses. Prevents crashes
 * when the ML model version changes (v1–v6 return different shapes)
 * or when fields are unexpectedly null / missing.
 *
 * Usage:
 *   import { PredictionResponseSchema } from '@/lib/schemas';
 *   const validated = PredictionResponseSchema.parse(raw);
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Prediction response - handles variance across model v1–v6
// ---------------------------------------------------------------------------

export const PredictionResponseSchema = z
  .object({
    prediction: z.union([z.literal(0), z.literal(1)]),
    probability: z.number().min(0).max(1),
    risk_level: z.union([z.literal(0), z.literal(1), z.literal(2)]),
    risk_label: z.enum(["Safe", "Alert", "Critical"]),
    confidence: z.number().min(0).max(1),
    model_version: z.string().default("unknown"),
    features_used: z.array(z.string()).default([]),
    timestamp: z.string().default(() => new Date().toISOString()),
    request_id: z.string().default(""),
    weather_data: z
      .object({
        temperature: z.number(),
        humidity: z.number(),
        precipitation: z.number(),
        wind_speed: z.number().optional(),
        pressure: z.number().optional(),
        source: z.string(),
        simulated: z.boolean().optional(),
      })
      .optional(),
    smart_alert: z
      .object({
        rainfall_3h: z.number(),
        confidence_score: z.number(),
        was_suppressed: z.boolean(),
        escalation_state: z.string(),
        escalation_reason: z.string().nullable(),
        contributing_factors: z.array(z.string()),
        original_risk_level: z.union([
          z.literal(0),
          z.literal(1),
          z.literal(2),
        ]),
      })
      .optional(),
    explanation: z
      .object({
        global_feature_importances: z.array(
          z.object({
            feature: z.string(),
            label: z.string(),
            importance: z.number(),
          }),
        ),
        prediction_contributions: z.array(
          z.object({
            feature: z.string(),
            label: z.string(),
            contribution: z.number(),
            abs_contribution: z.number(),
            direction: z.enum(["increases_risk", "decreases_risk"]),
          }),
        ),
        why_alert: z.object({
          summary: z.string(),
          risk_label: z.string(),
          confidence_pct: z.number(),
          factors: z.array(
            z.object({
              text: z.string(),
              severity: z.enum(["high", "medium", "low"]),
            }),
          ),
        }),
      })
      .optional(),
  })
  .passthrough(); // Don't throw on unknown fields from future versions

export type ValidatedPredictionResponse = z.infer<
  typeof PredictionResponseSchema
>;

// ---------------------------------------------------------------------------
// Alert - validates SSE and REST alert payloads
// ---------------------------------------------------------------------------

export const AlertSchema = z.object({
  id: z.number(),
  risk_level: z.union([z.literal(0), z.literal(1), z.literal(2)]),
  message: z.string(),
  location: z.string().optional(),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
  triggered_at: z.string(),
  expires_at: z.string().optional(),
  acknowledged: z.boolean(),
  created_at: z.string(),
  updated_at: z.string().optional(),
  confidence_score: z.number().optional(),
  rainfall_3h: z.number().optional(),
  escalation_state: z
    .enum(["initial", "escalated", "auto_escalated", "suppressed"])
    .optional(),
  escalation_reason: z.string().optional(),
  contributing_factors: z.array(z.string()).optional(),
});

export type ValidatedAlert = z.infer<typeof AlertSchema>;

// ---------------------------------------------------------------------------
// Weather data
// ---------------------------------------------------------------------------

export const WeatherDataSchema = z.object({
  id: z.number().optional(),
  temperature: z.number(),
  humidity: z.number(),
  precipitation: z.number(),
  wind_speed: z.number().optional(),
  pressure: z.number().optional(),
  recorded_at: z.string(),
  source: z.string().optional(),
  created_at: z.string().optional(),
});

export type ValidatedWeatherData = z.infer<typeof WeatherDataSchema>;

// ---------------------------------------------------------------------------
// Dashboard stats
// ---------------------------------------------------------------------------

export const DashboardStatsSchema = z.object({
  weather_data: z
    .object({
      temperature: z.number(),
      humidity: z.number(),
      precipitation: z.number(),
      wind_speed: z.number().optional(),
      pressure: z.number().optional(),
    })
    .nullable()
    .default(null),
  predictions: z
    .object({
      total: z.number(),
      safe: z.number(),
      alert: z.number(),
      critical: z.number(),
    })
    .nullable()
    .default(null),
  alerts: z
    .object({
      total: z.number(),
      pending: z.number(),
      acknowledged: z.number(),
    })
    .nullable()
    .default(null),
  risk_distribution_30d: z
    .object({
      safe: z.number(),
      alert: z.number(),
      critical: z.number(),
      average_risk: z.number(),
    })
    .nullable()
    .default(null),
});

export type ValidatedDashboardStats = z.infer<typeof DashboardStatsSchema>;

// ---------------------------------------------------------------------------
// Generic API response wrapper
// ---------------------------------------------------------------------------

export function apiResponseSchema<T extends z.ZodType>(dataSchema: T) {
  return z.object({
    success: z.boolean(),
    data: dataSchema,
    message: z.string().optional(),
    request_id: z.string().optional(),
  });
}

export function paginatedResponseSchema<T extends z.ZodType>(itemSchema: T) {
  return z.object({
    success: z.boolean(),
    data: z.array(itemSchema),
    total: z.number(),
    page: z.number(),
    limit: z.number(),
    pages: z.number(),
    request_id: z.string().optional(),
  });
}
