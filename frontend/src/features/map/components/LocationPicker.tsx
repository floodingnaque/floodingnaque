/**
 * LocationPicker Component
 *
 * Interactive map component for selecting a location with crosshair overlay.
 * Used for selecting coordinates for flood predictions.
 */

import { useState, useCallback, useRef } from 'react';
import { MapPin, Check, X, Crosshair } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { FloodMap, type FloodMapRef } from './FloodMap';

export interface LocationPickerProps {
  /** Initial latitude */
  initialLat?: number;
  /** Initial longitude */
  initialLng?: number;
  /** Callback when location is confirmed */
  onConfirm: (lat: number, lng: number) => void;
  /** Callback when picker is cancelled */
  onCancel?: () => void;
  /** Additional CSS classes */
  className?: string;
  /** Map height */
  height?: string | number;
}

export interface SelectedLocation {
  lat: number;
  lng: number;
}

/**
 * LocationPicker - Map-based location selection component
 *
 * @example
 * <LocationPicker
 *   onConfirm={(lat, lng) => console.log('Selected:', lat, lng)}
 *   onCancel={() => console.log('Cancelled')}
 * />
 */
export function LocationPicker({
  initialLat,
  initialLng,
  onConfirm,
  onCancel,
  className,
  height = 400,
}: LocationPickerProps) {
  const mapRef = useRef<FloodMapRef>(null);

  // Default to Parañaque City center
  const defaultLat = parseFloat(import.meta.env.VITE_MAP_DEFAULT_LAT || '14.4793');
  const defaultLng = parseFloat(import.meta.env.VITE_MAP_DEFAULT_LNG || '121.0198');

  const [selectedLocation, setSelectedLocation] = useState<SelectedLocation>({
    lat: initialLat ?? defaultLat,
    lng: initialLng ?? defaultLng,
  });

  // Handle click on map
  const handleLocationSelect = useCallback((lat: number, lng: number) => {
    setSelectedLocation({ lat, lng });
    // Center map on clicked location
    mapRef.current?.setView(lat, lng);
  }, []);

  // Confirm selection
  const handleConfirm = useCallback(() => {
    onConfirm(selectedLocation.lat, selectedLocation.lng);
  }, [selectedLocation, onConfirm]);

  // Cancel selection
  const handleCancel = useCallback(() => {
    onCancel?.();
  }, [onCancel]);

  // Reset to current location
  const handleReset = useCallback(() => {
    const lat = initialLat ?? defaultLat;
    const lng = initialLng ?? defaultLng;
    setSelectedLocation({ lat, lng });
    mapRef.current?.setView(lat, lng);
  }, [initialLat, initialLng, defaultLat, defaultLng]);

  // Map height to Tailwind classes - covers common use cases
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
    <div className={cn('space-y-4', className)}>
      {/* Instructions */}
      <div className="flex items-center gap-2 rounded-lg bg-muted p-3">
        <Crosshair className="h-5 w-5 text-primary" />
        <p className="text-sm text-muted-foreground">
          Drag the map or click to select a location. The crosshair shows the selected point.
        </p>
      </div>

      {/* Map Container with Crosshair */}
      <div className={cn('relative', heightClass)}>
        <FloodMap
          ref={mapRef}
          center={[selectedLocation.lat, selectedLocation.lng]}
          onLocationSelect={handleLocationSelect}
          height="100%"
          className="rounded-lg"
        />

        {/* Crosshair Overlay */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-1/2 h-8 w-0.5 -translate-x-1/2 -translate-y-full bg-primary/70" />
            <div className="absolute left-1/2 top-full h-8 w-0.5 -translate-x-1/2 bg-primary/70" />
            {/* Horizontal line */}
            <div className="absolute right-full top-1/2 h-0.5 w-8 -translate-y-1/2 bg-primary/70" />
            <div className="absolute left-full top-1/2 h-0.5 w-8 -translate-y-1/2 bg-primary/70" />
            {/* Center dot */}
            <div className="h-3 w-3 rounded-full border-2 border-primary bg-white shadow-md" />
          </div>
        </div>

        {/* Select Mode Indicator */}
        <div className="absolute bottom-2 left-2 z-[1000] rounded bg-white/90 px-2 py-1 text-xs shadow">
          <span className="font-medium text-primary">Select Mode</span>
        </div>
      </div>

      {/* Selected Coordinates Display */}
      <div className="flex items-center justify-between rounded-lg border bg-card p-4">
        <div className="flex items-center gap-3">
          <MapPin className="h-5 w-5 text-primary" />
          <div>
            <p className="text-sm font-medium">Selected Location</p>
            <p className="font-mono text-sm text-muted-foreground">
              {selectedLocation.lat.toFixed(6)}, {selectedLocation.lng.toFixed(6)}
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleReset}
          className="text-muted-foreground"
        >
          Reset
        </Button>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-3">
        {onCancel && (
          <Button variant="outline" onClick={handleCancel}>
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
        )}
        <Button onClick={handleConfirm}>
          <Check className="mr-2 h-4 w-4" />
          Confirm Location
        </Button>
      </div>
    </div>
  );
}

export default LocationPicker;
