/**
 * GlassCard — Glassmorphism Card Component
 *
 * A card with backdrop-blur, semi-transparent background,
 * and subtle border for modern Web 3.0 aesthetic.
 */

import { cn } from "@/lib/utils";
import * as React from "react";

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Intensity of glass effect: 'light' | 'medium' | 'heavy' */
  intensity?: "light" | "medium" | "heavy";
}

const intensityStyles = {
  light: "bg-card/90 backdrop-blur-sm border-border/50",
  medium:
    "bg-card/85 backdrop-blur-md border-border/40 shadow-lg shadow-black/5 dark:shadow-black/20",
  heavy:
    "bg-card/75 backdrop-blur-lg border-border/30 shadow-xl shadow-black/10 dark:shadow-black/30",
};

const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ className, intensity = "medium", ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-2xl border text-card-foreground transition-all duration-300",
        intensityStyles[intensity],
        className,
      )}
      {...props}
    />
  ),
);

GlassCard.displayName = "GlassCard";

export { GlassCard };
