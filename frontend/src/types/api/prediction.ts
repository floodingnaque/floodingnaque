export interface PredictionRequest {
  temperature: number; // Kelvin
  humidity: number; // Percentage 0-100
  precipitation: number; // mm
  wind_speed: number; // m/s
  pressure?: number; // hPa (optional)
}

/**
 * Location-based prediction request.
 * Sends coordinates and the backend fetches weather data automatically.
 */
export interface LocationPredictionRequest {
  latitude: number; // Decimal degrees
  longitude: number; // Decimal degrees
}

export interface PredictionResponse {
  prediction: 0 | 1;
  probability: number;
  risk_level: RiskLevel;
  risk_label: RiskLabel;
  confidence: number;
  model_version: string;
  features_used: string[];
  timestamp: string;
  request_id: string;
  /** Feature completeness tracking - indicates data quality of this prediction */
  feature_completeness?: {
    features_available: number;
    features_total: number;
    features_defaulted: string[];
    confidence_impact: "none" | "low" | "high";
    rolling_data_source: string;
    rolling_days_available: number;
  };
  /** Features filled with defaults when actual data was unavailable */
  imputed_defaults?: Record<string, number>;
  /** Weather data fetched from API (present in location-based predictions) */
  weather_data?: {
    temperature: number; // Kelvin
    humidity: number;
    precipitation: number;
    wind_speed?: number;
    pressure?: number;
    source: string;
    /** True when OWM_API_KEY is missing in dev mode and simulated data is used */
    simulated?: boolean;
  };
  /** Smart alert evaluation metadata */
  smart_alert?: {
    rainfall_3h: number;
    confidence_score: number;
    was_suppressed: boolean;
    escalation_state: string;
    escalation_reason: string | null;
    contributing_factors: string[];
    original_risk_level: RiskLevel;
  };
  /** Explainable AI payload */
  explanation?: XAIExplanation;
}

// ---------------------------------------------------------------------------
// XAI (Explainable AI) types
// ---------------------------------------------------------------------------

/** A single feature's global importance in the trained model. */
export interface FeatureImportance {
  feature: string;
  label: string;
  importance: number;
}

/** A single feature's per-prediction contribution (SHAP-like). */
export interface PredictionContribution {
  feature: string;
  label: string;
  contribution: number;
  abs_contribution: number;
  direction: "increases_risk" | "decreases_risk";
}

/** Why-alert factor with severity tag. */
export interface WhyAlertFactor {
  text: string;
  severity: "high" | "medium" | "low";
}

/** Full XAI explanation payload returned by the backend. */
export interface XAIExplanation {
  global_feature_importances: FeatureImportance[];
  prediction_contributions: PredictionContribution[];
  why_alert: {
    summary: string;
    risk_label: string;
    confidence_pct: number;
    factors: WhyAlertFactor[];
  };
}

export type RiskLevel = 0 | 1 | 2;
export type RiskLabel = "Safe" | "Alert" | "Critical";

export interface RiskConfig {
  level: RiskLevel;
  label: RiskLabel;
  color: string;
  bgColor: string;
  icon: string;
}

export const RISK_CONFIGS: Record<RiskLevel, RiskConfig> = {
  0: {
    level: 0,
    label: "Safe",
    color: "text-risk-safe",
    bgColor: "bg-risk-safe/15",
    icon: "CheckCircle",
  },
  1: {
    level: 1,
    label: "Alert",
    color: "text-risk-alert",
    bgColor: "bg-risk-alert/15",
    icon: "AlertTriangle",
  },
  2: {
    level: 2,
    label: "Critical",
    color: "text-risk-critical",
    bgColor: "bg-risk-critical/15",
    icon: "XCircle",
  },
};
