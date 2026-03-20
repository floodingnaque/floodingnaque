/**
 * Map Feature Module
 *
 * Barrel exports for the map feature including components
 * for flood visualization and location selection.
 */

// Components
export {
  EvacuationMarkers,
  type EvacuationMarkersProps,
} from "./components/EvacuationMarkers";
export {
  FloodMap,
  type FloodMapProps,
  type FloodMapRef,
} from "./components/FloodMap";
export {
  HazardOverlay,
  type HazardOverlayProps,
} from "./components/HazardOverlay";
export {
  LocationPicker,
  type LocationPickerProps,
  type SelectedLocation,
} from "./components/LocationPicker";
export {
  MapLayerControl,
  type BaseMapType,
  type LayerVisibility,
  type MapLayerControlProps,
} from "./components/MapLayerControl";
export { RiskMarkers, type RiskMarkersProps } from "./components/RiskMarkers";

// Hooks
export {
  hazardMapKeys,
  useHazardMap,
  type HazardFeature,
  type HazardFeatureProperties,
  type HazardMapData,
} from "./hooks/useHazardMap";
