/**
 * FloodMap Component
 *
 * Interactive Leaflet map centered on Parañaque City for flood visualization.
 * Supports alert markers, click handlers for location selection, and ref forwarding.
 */

import { forwardRef, useCallback, useImperativeHandle, useRef } from 'react';
import { MapContainer, TileLayer, useMapEvents } from 'react-leaflet';
import type { Map as LeafletMap, LeafletMouseEvent } from 'leaflet';
import 'leaflet/dist/leaflet.css';

import { cn } from '@/lib/utils';
import type { Alert } from '@/types';
import { RiskMarkers } from './RiskMarkers';

/**
 * Default map configuration from environment variables
 */
const DEFAULT_CENTER: [number, number] = [
  parseFloat(import.meta.env.VITE_MAP_DEFAULT_LAT || '14.4793'),
  parseFloat(import.meta.env.VITE_MAP_DEFAULT_LNG || '121.0198'),
];
const DEFAULT_ZOOM = parseInt(import.meta.env.VITE_MAP_DEFAULT_ZOOM || '13', 10);

export interface FloodMapProps {
  /** Map center coordinates [lat, lng] */
  center?: [number, number];
  /** Initial zoom level (default: 13) */
  zoom?: number;
  /** Alerts to display as markers */
  alerts?: Alert[];
  /** Callback when user clicks on map */
  onLocationSelect?: (lat: number, lng: number) => void;
  /** Additional CSS classes for the container */
  className?: string;
  /** Map height (default: 400px) */
  height?: string | number;
  /** Whether to show attribution */
  showAttribution?: boolean;
}

export interface FloodMapRef {
  /** Get the Leaflet map instance */
  getMap: () => LeafletMap | null;
  /** Fly to a specific location */
  flyTo: (lat: number, lng: number, zoom?: number) => void;
  /** Set view immediately without animation */
  setView: (lat: number, lng: number, zoom?: number) => void;
}

/**
 * Internal component to handle map events
 */
interface MapEventsHandlerProps {
  onLocationSelect?: (lat: number, lng: number) => void;
}

function MapEventsHandler({ onLocationSelect }: MapEventsHandlerProps) {
  useMapEvents({
    click: (e: LeafletMouseEvent) => {
      if (onLocationSelect) {
        onLocationSelect(e.latlng.lat, e.latlng.lng);
      }
    },
  });
  return null;
}

/**
 * FloodMap - Interactive map for flood visualization
 *
 * @example
 * // Basic usage
 * <FloodMap alerts={alerts} onLocationSelect={(lat, lng) => console.log(lat, lng)} />
 *
 * @example
 * // With ref
 * const mapRef = useRef<FloodMapRef>(null);
 * <FloodMap ref={mapRef} />
 * // Later: mapRef.current?.flyTo(14.48, 121.02)
 */
export const FloodMap = forwardRef<FloodMapRef, FloodMapProps>(
  (
    {
      center = DEFAULT_CENTER,
      zoom = DEFAULT_ZOOM,
      alerts = [],
      onLocationSelect,
      className,
      height = 400,
      showAttribution = true,
    },
    ref
  ) => {
    const mapRef = useRef<LeafletMap | null>(null);

    // Expose map methods via ref
    useImperativeHandle(
      ref,
      () => ({
        getMap: () => mapRef.current,
        flyTo: (lat: number, lng: number, flyZoom?: number) => {
          mapRef.current?.flyTo([lat, lng], flyZoom ?? zoom);
        },
        setView: (lat: number, lng: number, viewZoom?: number) => {
          mapRef.current?.setView([lat, lng], viewZoom ?? zoom);
        },
      }),
      [zoom]
    );

    // Store map instance when ready
    const handleMapReady = useCallback((map: LeafletMap) => {
      mapRef.current = map;
    }, []);

    // Map height to Tailwind classes - covers common use cases
    // For custom heights, use the className prop with arbitrary values like "h-[450px]"
    const heightClass = 
      height === '100%' ? 'h-full' :
      height === 200 ? 'h-[200px]' :
      height === 250 ? 'h-[250px]' :
      height === 300 ? 'h-[300px]' :
      height === 350 ? 'h-[350px]' :
      height === 400 ? 'h-[400px]' :
      height === 450 ? 'h-[450px]' :
      height === 500 ? 'h-[500px]' :
      height === 600 ? 'h-[600px]' :
      'h-[400px]'; // Default fallback

    return (
      <div
        className={cn(
          'relative overflow-hidden rounded-lg border shadow-md',
          heightClass,
          className
        )}
      >
        <MapContainer
          center={center}
          zoom={zoom}
          scrollWheelZoom={true}
          className="h-full w-full"
          ref={handleMapReady}
          attributionControl={showAttribution}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Map click handler */}
          {onLocationSelect && (
            <MapEventsHandler onLocationSelect={onLocationSelect} />
          )}

          {/* Alert markers */}
          {alerts.length > 0 && <RiskMarkers alerts={alerts} />}
        </MapContainer>
      </div>
    );
  }
);

FloodMap.displayName = 'FloodMap';

export default FloodMap;
