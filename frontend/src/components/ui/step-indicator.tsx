/**
 * StepIndicator - Multi-step form progress indicator
 *
 * Displays numbered circles connected by lines,
 * highlighting the current/completed steps.
 */

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface StepIndicatorProps {
  /** Total number of steps */
  steps: number;
  /** Current step (1-indexed) */
  current: number;
  /** Step labels */
  labels?: string[];
}

export function StepIndicator({ steps, current, labels }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-0">
      {Array.from({ length: steps }).map((_, i) => {
        const stepNum = i + 1;
        const isCompleted = stepNum < current;
        const isCurrent = stepNum === current;
        const isLast = stepNum === steps;

        return (
          <div key={i} className="flex items-center">
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold transition-all duration-500",
                  isCompleted &&
                    "bg-primary text-primary-foreground shadow-md shadow-primary/25",
                  isCurrent &&
                    "bg-primary text-primary-foreground ring-4 ring-primary/20 shadow-lg shadow-primary/30",
                  !isCompleted &&
                    !isCurrent &&
                    "bg-muted text-muted-foreground border border-border/50",
                )}
              >
                {isCompleted ? <Check className="h-3.5 w-3.5" /> : stepNum}
              </div>
              {labels && labels[i] && (
                <span
                  className={cn(
                    "text-[10px] font-medium transition-colors duration-300",
                    isCurrent || isCompleted
                      ? "text-foreground"
                      : "text-muted-foreground/60",
                  )}
                >
                  {labels[i]}
                </span>
              )}
            </div>

            {!isLast && (
              <div
                className={cn(
                  "mx-2 h-0.5 w-12 rounded-full transition-all duration-500",
                  isCompleted ? "bg-primary" : "bg-border/50",
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
