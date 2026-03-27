/**
 * Simulation API types
 */

export interface SimulationParams {
  temperature: number;
  humidity: number;
  precipitation: number;
  wind_speed?: number;
  pressure?: number;
  scenario?: "normal" | "heavy_monsoon" | "typhoon" | "high_tide_rain";
}

export interface SimulationResult {
  success: boolean;
  simulation: true;
  scenario: string;
  input: Record<string, number>;
  prediction: 0 | 1;
  probability: number;
  risk_level: 0 | 1 | 2;
  risk_label: "Safe" | "Alert" | "Critical";
  confidence: number;
  model_version: string;
  features_used: string[];
  explanation?: {
    global_feature_importances: Array<{
      feature: string;
      label: string;
      importance: number;
    }>;
    prediction_contributions: Array<{
      feature: string;
      label: string;
      contribution: number;
      abs_contribution: number;
      direction: "increases_risk" | "decreases_risk";
    }>;
    why_alert: {
      summary: string;
      risk_label: string;
      confidence_pct: number;
      factors: Array<{ text: string; severity: "high" | "medium" | "low" }>;
    };
  };
  request_id: string;
}
