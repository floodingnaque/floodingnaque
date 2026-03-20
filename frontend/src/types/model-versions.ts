/**
 * Model Version Capabilities
 *
 * Maps each progressive training version (v1–v6) to its feature
 * support flags and metrics. Used by normalizePredictionResponse
 * to provide safe defaults when a field isn't supported by the
 * active model version.
 */

export type ModelVersion = "v1" | "v2" | "v3" | "v4" | "v5" | "v6";

export interface ModelCapabilities {
  hasTidalData: boolean;
  hasRollingFeatures: boolean;
  hasRiskColor: boolean;
  hasInteractionTerms: boolean;
  accuracy: number;
  features: number;
}

export const MODEL_CAPABILITIES: Record<ModelVersion, ModelCapabilities> = {
  v1: {
    hasTidalData: false,
    hasRollingFeatures: false,
    hasRiskColor: false,
    hasInteractionTerms: false,
    accuracy: 0.7832,
    features: 4,
  },
  v2: {
    hasTidalData: false,
    hasRollingFeatures: false,
    hasRiskColor: false,
    hasInteractionTerms: true,
    accuracy: 0.8345,
    features: 6,
  },
  v3: {
    hasTidalData: false,
    hasRollingFeatures: false,
    hasRiskColor: false,
    hasInteractionTerms: true,
    accuracy: 0.8891,
    features: 8,
  },
  v4: {
    hasTidalData: false,
    hasRollingFeatures: true,
    hasRiskColor: false,
    hasInteractionTerms: true,
    accuracy: 0.9234,
    features: 9,
  },
  v5: {
    hasTidalData: true,
    hasRollingFeatures: true,
    hasRiskColor: false,
    hasInteractionTerms: true,
    accuracy: 0.9512,
    features: 10,
  },
  v6: {
    hasTidalData: true,
    hasRollingFeatures: true,
    hasRiskColor: true,
    hasInteractionTerms: true,
    accuracy: 0.9675,
    features: 10,
  },
};

/**
 * Check if a string is a valid model version key.
 */
export function isModelVersion(v: string): v is ModelVersion {
  return v in MODEL_CAPABILITIES;
}
