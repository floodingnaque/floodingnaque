import { cn } from "@/lib/utils";

interface SvgGaugeProps {
  /** Current value */
  value: number;
  /** Maximum value */
  max: number;
  /** Threshold above which the gauge shows danger */
  dangerThreshold?: number;
  /** Threshold above which the gauge shows warning */
  warnThreshold?: number;
  /** Unit label beneath the value (e.g. "m", "mm") */
  unit?: string;
  /** Text label below the gauge */
  label?: string;
  /** Diameter in px (default 160) */
  size?: number;
  className?: string;
}

export function SvgGauge({
  value,
  max,
  dangerThreshold,
  warnThreshold,
  unit = "",
  label,
  size = 160,
  className,
}: SvgGaugeProps) {
  const radius = 58;
  const stroke = 10;
  const center = 70;
  // 270° arc (from 135° to 405°)
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * 0.75; // 270°
  const clamped = Math.max(0, Math.min(value, max));
  const progress = max > 0 ? clamped / max : 0;
  const dashOffset = arcLength * (1 - progress);

  // Color based on thresholds
  let strokeColor = "hsl(var(--chart-2))"; // safe green
  if (dangerThreshold != null && value >= dangerThreshold) {
    strokeColor = "hsl(var(--destructive))";
  } else if (warnThreshold != null && value >= warnThreshold) {
    strokeColor = "hsl(var(--chart-4))"; // amber/warning
  }

  return (
    <div className={cn("flex flex-col items-center", className)}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 140 140"
        className="overflow-visible"
      >
        {/* Background arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={stroke}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={0}
          strokeLinecap="round"
          transform={`rotate(135 ${center} ${center})`}
        />
        {/* Value arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={stroke}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform={`rotate(135 ${center} ${center})`}
          className="transition-all duration-700 ease-out"
        />
        {/* Center text */}
        <text
          x={center}
          y={center - 4}
          textAnchor="middle"
          className="fill-foreground text-2xl font-bold"
          style={{ fontSize: 24 }}
        >
          {value.toFixed(1)}
        </text>
        {unit && (
          <text
            x={center}
            y={center + 16}
            textAnchor="middle"
            className="fill-muted-foreground text-xs"
            style={{ fontSize: 12 }}
          >
            {unit}
          </text>
        )}
      </svg>
      {label && (
        <span className="mt-1 text-xs font-medium text-muted-foreground">
          {label}
        </span>
      )}
    </div>
  );
}
