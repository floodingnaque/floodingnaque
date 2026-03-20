/**
 * ReportFAB Component
 *
 * Floating action button for submitting a new flood report.
 * Positioned at bottom-right with a pulse animation when
 * an active flood alert is present.
 */

import { Waves } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface ReportFABProps {
  /** Called when the FAB is clicked */
  onClick: () => void;
  /** Whether to show the pulse animation */
  pulse?: boolean;
  className?: string;
}

export function ReportFAB({
  onClick,
  pulse = false,
  className,
}: ReportFABProps) {
  return (
    <Button
      onClick={onClick}
      size="lg"
      className={cn(
        "fixed bottom-6 right-6 z-50",
        "h-14 w-14 rounded-full shadow-lg",
        "bg-blue-600 hover:bg-blue-700 text-white",
        "transition-transform hover:scale-105 active:scale-95",
        pulse && "animate-pulse",
        className,
      )}
      aria-label="Report Flood"
    >
      <Waves className="h-6 w-6" />
    </Button>
  );
}
