/**
 * Flooding Feature Module
 *
 * Barrel exports for all flooding-related components, hooks, services, and utilities.
 */

// Components
export { ExplainabilityPanel } from "./components/ExplainabilityPanel";
export { PersonalizedRiskBanner } from "./components/PersonalizedRiskBanner";
export { PredictionForm } from "./components/PredictionForm";
export { PredictionResult } from "./components/PredictionResult";
export { ResidentDecisionPanel } from "./components/ResidentDecisionPanel";
export { RiskBadge } from "./components/RiskBadge";
export { RiskDisplay } from "./components/RiskDisplay";

// Hooks
export { useFloodStatus } from "./hooks/useFloodStatus";
export { useLivePrediction } from "./hooks/useLivePrediction";
export {
  useLocationPrediction,
  type UseLocationPredictionOptions,
} from "./hooks/useLocationPrediction";
export {
  usePrediction,
  type UsePredictionOptions,
} from "./hooks/usePrediction";

// Services
export { predictionApi } from "./services/predictionApi";

// Utils
export {
  celsiusToKelvin,
  formatTemperature,
  kelvinToCelsius,
} from "./utils/temperature";
