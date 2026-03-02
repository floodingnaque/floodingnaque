/**
 * RouteErrorBoundary Component
 *
 * Wrapper around ErrorBoundary tailored for route-level errors.
 * Provides differentiated handling for 404 vs generic errors
 * with navigation options to return to the dashboard.
 */

import { type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, FileQuestion, Home, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { ErrorBoundary } from './ErrorBoundary';

// ---------------------------------------------------------------------------
// 404 fallback
// ---------------------------------------------------------------------------

/**
 * Displayed when a route is not found.
 */
export function NotFoundFallback() {
  const navigate = useNavigate();

  return (
    <div
      className="flex items-center justify-center min-h-[60vh] p-6"
      role="alert"
      aria-live="polite"
    >
      <Card className="w-full max-w-lg text-center">
        <CardHeader className="pb-4">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-muted">
            <FileQuestion
              className="h-7 w-7 text-muted-foreground"
              aria-hidden="true"
            />
          </div>
          <CardTitle className="text-xl">Page not found</CardTitle>
          <CardDescription>
            The page you&apos;re looking for doesn&apos;t exist or has been
            moved.
          </CardDescription>
        </CardHeader>
        <CardFooter className="flex justify-center gap-3 pt-2">
          <Button variant="outline" onClick={() => navigate(-1)}>
            <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
            Go Back
          </Button>
          <Button onClick={() => navigate('/dashboard')}>
            <Home className="mr-2 h-4 w-4" aria-hidden="true" />
            Dashboard
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Route-level error fallback (generic)
// ---------------------------------------------------------------------------

/**
 * Displayed when an uncaught error occurs inside a route.
 */
function RouteErrorFallback() {
  const navigate = useNavigate();

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
            This page encountered an unexpected error. Try navigating back or
            returning to the dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            If this problem persists, please contact support.
          </p>
        </CardContent>
        <CardFooter className="flex justify-center gap-3 pt-2">
          <Button variant="outline" onClick={() => navigate(-1)}>
            <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
            Go Back
          </Button>
          <Button onClick={() => navigate('/dashboard')}>
            <Home className="mr-2 h-4 w-4" aria-hidden="true" />
            Dashboard
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// RouteErrorBoundary
// ---------------------------------------------------------------------------

interface RouteErrorBoundaryProps {
  children: ReactNode;
}

/**
 * Wraps route content with an ErrorBoundary that renders
 * a route-appropriate fallback UI.
 */
export function RouteErrorBoundary({ children }: RouteErrorBoundaryProps) {
  return (
    <ErrorBoundary fallback={<RouteErrorFallback />}>
      {children}
    </ErrorBoundary>
  );
}

export default RouteErrorBoundary;
