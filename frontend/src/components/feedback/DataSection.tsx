/**
 * DataSection Component
 *
 * Wrapper that enforces consistent loading, error, and empty
 * states across every data-fetching section in every dashboard.
 */

interface DataSectionProps {
  isLoading: boolean;
  isError: boolean;
  isEmpty?: boolean;
  error?: Error | null;
  /** Skeleton to show while loading */
  skeleton: React.ReactNode;
  /** Content to show when data set is empty */
  empty?: React.ReactNode;
  /** The actual content when data is available */
  children: React.ReactNode;
  /** Retry handler shown in error state */
  onRetry?: () => void;
}

export function DataSection({
  isLoading,
  isError,
  isEmpty,
  error,
  skeleton,
  empty,
  children,
  onRetry,
}: DataSectionProps) {
  if (isLoading) return <>{skeleton}</>;

  if (isError) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-center">
        <p className="text-sm text-destructive mb-3">
          {error?.message ?? "Failed to load data"}
        </p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="text-xs text-primary underline"
          >
            Try again
          </button>
        )}
      </div>
    );
  }

  if (isEmpty && empty) return <>{empty}</>;

  return <>{children}</>;
}
