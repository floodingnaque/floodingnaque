/**
 * MapErrorBoundary - Specialized error boundary for Leaflet map components.
 *
 * Catches Leaflet-specific rendering errors (tile load failures,
 * WebGL context loss, invalid GeoJSON, etc.) and renders a
 * compact recovery UI sized to match the map container.
 */

import { Button } from "@/components/ui/button";
import { captureException } from "@/lib/sentry";
import { MapPin, RefreshCw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

interface MapErrorBoundaryProps {
  children: ReactNode;
  /** Optional custom fallback */
  fallback?: ReactNode;
  /** CSS class for the fallback container */
  className?: string;
}

interface MapErrorBoundaryState {
  hasError: boolean;
}

export class MapErrorBoundary extends Component<
  MapErrorBoundaryProps,
  MapErrorBoundaryState
> {
  constructor(props: MapErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): MapErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    captureException(error, {
      context: "MapErrorBoundary",
      componentStack: info.componentStack ?? undefined,
    });
  }

  private handleRetry = (): void => {
    this.setState({ hasError: false });
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    return (
      <div
        className={`flex flex-col items-center justify-center gap-3 rounded-lg border bg-muted/50 p-8 text-center ${this.props.className ?? "h-100"}`}
        role="alert"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
          <MapPin className="h-6 w-6 text-destructive" />
        </div>
        <p className="text-sm font-medium text-muted-foreground">
          Unable to load the map. This may be a temporary issue.
        </p>
        <Button variant="outline" size="sm" onClick={this.handleRetry}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Retry
        </Button>
      </div>
    );
  }
}
