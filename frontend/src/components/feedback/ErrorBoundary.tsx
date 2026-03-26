/**
 * ErrorBoundary Component
 *
 * React class component that catches JavaScript errors anywhere in its
 * child component tree and renders a fallback UI instead of crashing.
 */

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { captureException } from "@/lib/sentry";
import { AlertTriangle, Home, RefreshCw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ErrorBoundaryProps {
  /** Child components to render when there's no error */
  children: ReactNode;
  /** Optional custom fallback UI */
  fallback?: ReactNode;
  /** Called when an error is caught */
  onError?: (error: Error, info: ErrorInfo) => void;
  /** Whether to show error details (defaults to dev mode) */
  showDetails?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * ErrorBoundary catches render-time errors and displays a recovery UI.
 *
 * @example
 * ```tsx
 * <ErrorBoundary>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Log to console in development
    console.error("[ErrorBoundary] Caught error:", error, info);

    // Report to Sentry in production (no-op when DSN is empty)
    captureException(error, {
      componentStack: info.componentStack ?? undefined,
      boundary: "ErrorBoundary",
    });

    // Clear auth state on authentication-related render crashes
    // so the user is redirected to login instead of a broken page.
    if (
      error.message?.includes("401") ||
      error.message?.includes("Unauthorized") ||
      error.message?.includes("token")
    ) {
      try {
        // Dynamic require in error boundary - can't use static import in class lifecycle
        // @ts-expect-error -- require is provided by bundler at runtime
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const mod = require("@/state/stores/authStore");
        mod.useAuthStore.getState().logout?.();
      } catch {
        // Auth store may not be available - safe to ignore
      }
    }

    // Notify parent if callback provided
    this.props.onError?.(error, info);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  private handleGoHome = (): void => {
    this.setState({ hasError: false, error: null });
    window.location.href = "/";
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    // Use custom fallback if provided
    if (this.props.fallback) {
      return this.props.fallback;
    }

    const isDev = this.props.showDetails ?? import.meta.env.DEV;

    return (
      <div
        className="flex items-center justify-center min-h-[60vh] p-6"
        role="alert"
        aria-live="assertive"
      >
        <Card className="w-full max-w-lg text-center">
          <CardHeader className="pb-4">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
              <AlertTriangle
                className="h-7 w-7 text-destructive"
                aria-hidden="true"
              />
            </div>
            <CardTitle className="text-xl">Something went wrong</CardTitle>
            <CardDescription>
              An unexpected error occurred. You can try again or return to the
              home page.
            </CardDescription>
          </CardHeader>

          {isDev && this.state.error && (
            <CardContent>
              <details className="text-left">
                <summary className="cursor-pointer text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                  Error details
                </summary>
                <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs font-mono text-destructive whitespace-pre-wrap wrap-break-word">
                  {this.state.error.message}
                  {this.state.error.stack && (
                    <>
                      {"\n\n"}
                      {this.state.error.stack}
                    </>
                  )}
                </pre>
              </details>
            </CardContent>
          )}

          <CardFooter className="flex justify-center gap-3 pt-2">
            <Button variant="outline" onClick={this.handleGoHome}>
              <Home className="mr-2 h-4 w-4" aria-hidden="true" />
              Go Home
            </Button>
            <Button onClick={this.handleReset}>
              <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
              Try Again
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }
}

export default ErrorBoundary;
