/**
 * LoadingSpinner Component
 *
 * Animated loading spinner using Lucide's Loader2 icon.
 * Supports different sizes and optional fullscreen mode.
 */

import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  /** Size of the spinner */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to display fullscreen centered */
  fullscreen?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Accessible label for screen readers */
  label?: string;
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-8 w-8',
  lg: 'h-12 w-12',
};

/**
 * Displays an animated loading spinner.
 *
 * @example
 * // Basic usage
 * <LoadingSpinner />
 *
 * @example
 * // Large spinner centered fullscreen
 * <LoadingSpinner size="lg" fullscreen />
 *
 * @example
 * // Small inline spinner
 * <LoadingSpinner size="sm" />
 */
export function LoadingSpinner({
  size = 'md',
  fullscreen = false,
  className,
  label = 'Loading...',
}: LoadingSpinnerProps) {
  const spinner = (
    <Loader2
      className={cn(
        'animate-spin text-primary',
        sizeClasses[size],
        className
      )}
      aria-hidden="true"
    />
  );

  if (fullscreen) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
        role="status"
        aria-live="polite"
        aria-label={label}
      >
        <div className="flex flex-col items-center gap-3">
          {spinner}
          <span className="sr-only">{label}</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex items-center justify-center"
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      {spinner}
      <span className="sr-only">{label}</span>
    </div>
  );
}

/**
 * Inline variant that can be used within text or buttons.
 */
export function LoadingSpinnerInline({
  size = 'sm',
  className,
}: Pick<LoadingSpinnerProps, 'size' | 'className'>) {
  return (
    <Loader2
      className={cn('animate-spin', sizeClasses[size], className)}
      aria-hidden="true"
    />
  );
}

export default LoadingSpinner;
