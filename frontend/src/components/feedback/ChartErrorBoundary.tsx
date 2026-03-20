/**
 * ChartErrorBoundary - Specialized error boundary for Recharts components.
 *
 * Catches chart rendering errors (invalid data shapes, SVG failures,
 * responsive container issues) and renders a compact recovery UI.
 */

import { Button } from "@/components/ui/button";
import { captureException } from "@/lib/sentry";
import { BarChart3, RefreshCw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

interface ChartErrorBoundaryProps {
  children: ReactNode;
  /** Optional custom fallback */
  fallback?: ReactNode;
  /** CSS class for the fallback container */
  className?: string;
}

interface ChartErrorBoundaryState {
  hasError: boolean;
}

export class ChartErrorBoundary extends Component<
  ChartErrorBoundaryProps,
  ChartErrorBoundaryState
> {
  constructor(props: ChartErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ChartErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    captureException(error, {
      context: "ChartErrorBoundary",
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
        className={`flex flex-col items-center justify-center gap-3 rounded-lg border bg-muted/50 p-6 text-center ${this.props.className ?? "h-64"}`}
        role="alert"
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10">
          <BarChart3 className="h-5 w-5 text-destructive" />
        </div>
        <p className="text-sm font-medium text-muted-foreground">
          Unable to render chart data.
        </p>
        <Button variant="outline" size="sm" onClick={this.handleRetry}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Retry
        </Button>
      </div>
    );
  }
}
