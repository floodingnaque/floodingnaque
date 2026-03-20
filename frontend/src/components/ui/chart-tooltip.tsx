import { cn } from "@/lib/utils";

interface ChartTooltipPayloadEntry {
  name?: string;
  value?: number;
  color?: string;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: ChartTooltipPayloadEntry[];
  label?: string;
  /** Unit appended after the value (e.g. " mm", " m") */
  unit?: string;
}

export function ChartTooltip({
  active,
  payload,
  label,
  unit = "",
}: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <div
      className={cn(
        "rounded-lg border bg-card px-3 py-2 text-xs shadow-md",
        "border-border/60 text-card-foreground",
      )}
    >
      <p className="mb-1 font-medium text-muted-foreground">{label}</p>
      {payload.map((entry: ChartTooltipPayloadEntry, i: number) => (
        <p
          key={i}
          className="font-mono font-semibold"
          style={{ color: entry.color }}
        >
          {entry.name}:{" "}
          {typeof entry.value === "number"
            ? entry.value.toFixed(1)
            : entry.value}
          {unit}
        </p>
      ))}
    </div>
  );
}
