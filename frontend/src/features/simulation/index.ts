/**
 * Simulation Feature Module
 *
 * What-if flood prediction interface with scenario presets,
 * parameter sliders, and explainability output.
 */

// Services
export { simulationApi } from "./services/simulationApi";

// Hooks
export { simulationKeys, useSimulation } from "./hooks/useSimulation";

// Types
export type { SimulationParams, SimulationResult } from "./types";

// Components
export {
  SimulationPanel,
  SimulationPanelSkeleton,
} from "./components/SimulationPanel";
