import { cn } from "@/lib/utils";

interface PulsingDotProps {
  color?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeMap = { sm: "h-2 w-2", md: "h-2.5 w-2.5", lg: "h-3 w-3" };

export function PulsingDot({ color, size = "md", className }: PulsingDotProps) {
  return (
    <span className={cn("relative inline-flex", className)}>
      <span
        className={cn(
          "animate-ping absolute inline-flex rounded-full opacity-75",
          sizeMap[size],
        )}
        style={color ? { backgroundColor: color } : undefined}
      />
      <span
        className={cn("relative inline-flex rounded-full", sizeMap[size])}
        style={color ? { backgroundColor: color } : undefined}
      />
    </span>
  );
}
