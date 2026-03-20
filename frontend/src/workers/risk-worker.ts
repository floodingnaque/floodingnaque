/**
 * Risk Classification Worker
 *
 * Offloads the risk-classification logic (Safe / Alert / Critical)
 * from the main thread so the UI stays responsive during batch
 * predictions.
 */

import { expose } from "comlink";

export interface RiskInput {
  flood_probability: number;
  precipitation: number;
  humidity: number;
}

export type RiskLevel = 0 | 1 | 2;
export type RiskLabel = "Safe" | "Alert" | "Critical";

interface RiskResult {
  level: RiskLevel;
  label: RiskLabel;
  confidence: number;
}

/**
 * Classify a single prediction into Safe (0), Alert (1), or Critical (2).
 *
 * Mirrors the backend RiskClassifier thresholds:
 *   Critical: probability >= 0.7 OR (probability >= 0.5 AND precipitation >= 50)
 *   Alert:    probability >= 0.4 OR (precipitation >= 30 AND humidity >= 80)
 *   Safe:     everything else
 */
function classify(input: RiskInput): RiskResult {
  const { flood_probability, precipitation, humidity } = input;

  if (
    flood_probability >= 0.7 ||
    (flood_probability >= 0.5 && precipitation >= 50)
  ) {
    return { level: 2, label: "Critical", confidence: flood_probability };
  }

  if (flood_probability >= 0.4 || (precipitation >= 30 && humidity >= 80)) {
    return { level: 1, label: "Alert", confidence: flood_probability };
  }

  return { level: 0, label: "Safe", confidence: 1 - flood_probability };
}

/**
 * Batch-classify an array of predictions.
 */
function classifyBatch(inputs: RiskInput[]): RiskResult[] {
  return inputs.map(classify);
}

const riskWorkerApi = {
  classify,
  classifyBatch,
};

export type RiskWorkerApi = typeof riskWorkerApi;

expose(riskWorkerApi);
