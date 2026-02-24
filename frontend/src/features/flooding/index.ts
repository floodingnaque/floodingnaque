/**
 * Flooding Feature Module
 *
 * Barrel exports for all flooding-related components, hooks, services, and utilities.
 */

// Components
export { PredictionForm } from './components/PredictionForm';
export { PredictionResult } from './components/PredictionResult';
export { RiskDisplay } from './components/RiskDisplay';

// Hooks
export { usePrediction, type UsePredictionOptions } from './hooks/usePrediction';
export {
  useLocationPrediction,
  type UseLocationPredictionOptions,
} from './hooks/useLocationPrediction';

// Services
export { predictionApi } from './services/predictionApi';

// Utils
export {
  celsiusToKelvin,
  kelvinToCelsius,
  formatTemperature,
} from './utils/temperature';
