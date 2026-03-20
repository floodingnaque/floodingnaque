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
export { RiskDisplay } from "./components/RiskDisplay";

// Hooks
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
