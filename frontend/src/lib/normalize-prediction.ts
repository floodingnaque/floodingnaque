/**
 * Normalize Prediction Response
 *
 * Adapts raw prediction API responses based on the active model's
 * capabilities. Provides safe defaults for fields not supported
 * by older model versions.
 */

import type { PredictionResponse, RiskLevel } from "@/types";
import { RISK_CONFIGS } from "@/types/api/prediction";
import {
  MODEL_CAPABILITIES,
  isModelVersion,
  type ModelVersion,
} from "@/types/model-versions";

export interface NormalizedPrediction extends PredictionResponse {
  /** Resolved risk color (CSS class), falls back to RISK_CONFIGS if model lacks riskColor */
  riskColor: string;
  /** Tidal contribution value, null if model doesn't support tidal data */
  tidalContribution: number | null;
  /** 7-day rolling precipitation, null if model lacks rolling features */
  rollingPrecip7d: number | null;
  /** Model version as typed enum */
  resolvedVersion: ModelVersion;
}

/**
 * Normalize a raw prediction response with version-aware defaults.
 */
export function normalizePredictionResponse(
  raw: PredictionResponse,
): NormalizedPrediction {
  const versionStr = raw.model_version ?? "v6";
  const resolvedVersion: ModelVersion = isModelVersion(versionStr)
    ? versionStr
    : "v6";
  const caps = MODEL_CAPABILITIES[resolvedVersion];

  const riskLevel: RiskLevel = raw.risk_level ?? 0;

  // Cast for potential extra fields from newer APIs
  const extra = raw as unknown as Record<string, unknown>;

  return {
    ...raw,
    resolvedVersion,
    riskColor: RISK_CONFIGS[riskLevel].color,
    tidalContribution: caps.hasTidalData
      ? ((extra.tidal_contribution as number) ?? null)
      : null,
    rollingPrecip7d: caps.hasRollingFeatures
      ? ((extra.rolling_precip_7d as number) ?? null)
      : null,
  };
}
