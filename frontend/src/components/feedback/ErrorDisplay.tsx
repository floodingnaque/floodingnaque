/**
 * ErrorDisplay Component
 * 
 * Displays error messages with optional retry functionality.
 * Handles different error types including ApiError.
 */

import { AlertCircle, RefreshCw } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ApiError } from '@/types';

interface ErrorDisplayProps {
  /** The error to display (Error, ApiError, or null) */
  error: Error | ApiError | null;
  /** Optional retry function - shows retry button if provided */
  retry?: () => void;
  /** Optional title override */
  title?: string;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show a compact version */
  compact?: boolean;
}

/**
 * Type guard to check if error is an ApiError.
 */
function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    'status' in error &&
    'message' in error
  );
}

/**
 * Extract a user-friendly message from various error types.
 */
function getErrorMessage(error: Error | ApiError | null): string {
  if (!error) {
    return 'An unknown error occurred';
  }

  if (isApiError(error)) {
    // API errors have structured messages
    return error.message || `Error ${error.code}: ${error.status}`;
  }

  if (error instanceof Error) {
    return error.message || 'An unexpected error occurred';
  }

  // Fallback for unknown error shapes
  if (typeof error === 'object' && 'message' in error) {
    return String((error as { message: unknown }).message);
  }

  return 'An unknown error occurred';
}

/**
 * Get additional error details for display.
 */
function getErrorDetails(error: Error | ApiError | null): string | null {
  if (!error) return null;

  if (isApiError(error)) {
    const details: string[] = [];
    if (error.code) details.push(`Code: ${error.code}`);
    if (error.status) details.push(`Status: ${error.status}`);
    if (error.details && Object.keys(error.details).length > 0) {
      details.push(`Details: ${JSON.stringify(error.details)}`);
    }
    return details.length > 0 ? details.join(' • ') : null;
  }

  // For regular errors, check for cause
  if (error instanceof Error && error.cause) {
    return String(error.cause);
  }

  return null;
}

/**
 * Displays an error message with optional retry functionality.
 * 
 * @example
 * // Basic error display
 * <ErrorDisplay error={new Error('Something went wrong')} />
 * 
 * @example
 * // With retry button
 * <ErrorDisplay 
 *   error={apiError} 
 *   retry={() => refetch()} 
 *   title="Failed to load data"
 * />
 * 
 * @example
 * // Compact version for inline display
 * <ErrorDisplay error={error} compact />
 */
export function ErrorDisplay({
  error,
  retry,
  title,
  className,
  compact = false,
}: ErrorDisplayProps) {
  // Don't render if no error
  if (!error) {
    return null;
  }

  const message = getErrorMessage(error);
  const details = getErrorDetails(error);
  const displayTitle = title || (isApiError(error) ? 'API Error' : 'Error');

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-2 text-sm text-destructive',
          className
        )}
        role="alert"
      >
        <AlertCircle className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
        <span className="truncate">{message}</span>
        {retry && (
          <Button
            variant="ghost"
            size="sm"
            onClick={retry}
            className="h-6 px-2 text-xs"
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
        )}
      </div>
    );
  }

  return (
    <Alert
      variant="destructive"
      className={cn('', className)}
      role="alert"
    >
      <AlertCircle className="h-4 w-4" aria-hidden="true" />
      <AlertTitle>{displayTitle}</AlertTitle>
      <AlertDescription className="mt-2">
        <p>{message}</p>
        {details && (
          <p className="mt-1 text-xs opacity-80 font-mono">{details}</p>
        )}
        {retry && (
          <Button
            variant="outline"
            size="sm"
            onClick={retry}
            className="mt-3"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}

export default ErrorDisplay;
