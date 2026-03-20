/**
 * DataUnavailable Component
 *
 * Reusable fallback for panels where data cannot be loaded or is temporarily missing.
 */

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AlertCircle } from "lucide-react";
import { type ElementType } from "react";

interface DataUnavailableAction {
  label: string;
  onClick: () => void;
}

interface DataUnavailableProps {
  title?: string;
  description?: string;
  icon?: ElementType;
  action?: DataUnavailableAction;
  className?: string;
  compact?: boolean;
}

export function DataUnavailable({
  title = "Data unavailable",
  description = "Please try again in a moment.",
  icon: Icon = AlertCircle,
  action,
  className,
  compact = false,
}: DataUnavailableProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        compact ? "py-4" : "py-8",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <div
        className={cn(
          "rounded-full bg-muted",
          compact ? "p-2 mb-2" : "p-3 mb-3",
        )}
      >
        <Icon
          className={cn(
            compact ? "h-4 w-4" : "h-5 w-5",
            "text-muted-foreground",
          )}
          aria-hidden="true"
        />
      </div>

      <p
        className={cn(
          compact ? "text-sm font-medium" : "text-base font-medium",
        )}
      >
        {title}
      </p>
      <p
        className={cn(
          "mt-1 text-muted-foreground",
          compact ? "text-xs" : "text-sm",
        )}
      >
        {description}
      </p>

      {action && (
        <Button
          variant="outline"
          size="sm"
          onClick={action.onClick}
          className="mt-3"
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}

export default DataUnavailable;
