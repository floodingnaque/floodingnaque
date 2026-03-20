/**
 * DateRangeFilter Component
 *
 * Date range selector with preset options for filtering weather data.
 * Provides quick presets and manual date input.
 */

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { format, subDays } from "date-fns";
import { Calendar, X } from "lucide-react";

export interface DateRange {
  start_date?: string;
  end_date?: string;
}

interface DateRangeFilterProps {
  /** Current date range values */
  value: DateRange;
  /** Callback when date range changes */
  onChange: (range: DateRange) => void;
}

/**
 * Preset date range options
 */
interface Preset {
  label: string;
  getValue: () => DateRange;
}

const presets: Preset[] = [
  {
    label: "Today",
    getValue: () => {
      const today = format(new Date(), "yyyy-MM-dd");
      return { start_date: today, end_date: today };
    },
  },
  {
    label: "Last 7 days",
    getValue: () => {
      const today = new Date();
      return {
        start_date: format(subDays(today, 7), "yyyy-MM-dd"),
        end_date: format(today, "yyyy-MM-dd"),
      };
    },
  },
  {
    label: "Last 30 days",
    getValue: () => {
      const today = new Date();
      return {
        start_date: format(subDays(today, 30), "yyyy-MM-dd"),
        end_date: format(today, "yyyy-MM-dd"),
      };
    },
  },
  {
    label: "Last 90 days",
    getValue: () => {
      const today = new Date();
      return {
        start_date: format(subDays(today, 90), "yyyy-MM-dd"),
        end_date: format(today, "yyyy-MM-dd"),
      };
    },
  },
];

/**
 * DateRangeFilter component
 *
 * @example
 * <DateRangeFilter
 *   value={{ start_date: '2026-01-01', end_date: '2026-01-31' }}
 *   onChange={(range) => setDateRange(range)}
 * />
 */
export function DateRangeFilter({ value, onChange }: DateRangeFilterProps) {
  // Handle preset selection
  const handlePreset = (preset: Preset) => {
    onChange(preset.getValue());
  };

  // Handle start date change
  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...value,
      start_date: e.target.value || undefined,
    });
  };

  // Handle end date change
  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...value,
      end_date: e.target.value || undefined,
    });
  };

  // Clear date range
  const handleClear = () => {
    onChange({ start_date: undefined, end_date: undefined });
  };

  // Check if range is active
  const hasRange = value.start_date || value.end_date;

  return (
    <div className="space-y-4">
      {/* Date inputs */}
      <div className="flex flex-wrap gap-4 items-end">
        <div className="flex-1 min-w-37.5">
          <Label htmlFor="start-date" className="text-sm font-medium">
            From
          </Label>
          <div className="relative mt-1">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              id="start-date"
              type="date"
              value={value.start_date || ""}
              max={value.end_date || undefined}
              onChange={handleStartDateChange}
              className="pl-10"
            />
          </div>
        </div>

        <div className="flex-1 min-w-37.5">
          <Label htmlFor="end-date" className="text-sm font-medium">
            To
          </Label>
          <div className="relative mt-1">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              id="end-date"
              type="date"
              value={value.end_date || ""}
              min={value.start_date || undefined}
              onChange={handleEndDateChange}
              className="pl-10"
            />
          </div>
        </div>

        {hasRange && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleClear}
            title="Clear dates"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Preset buttons */}
      <div className="flex flex-wrap gap-2">
        {presets.map((preset) => (
          <Button
            key={preset.label}
            variant="outline"
            size="sm"
            onClick={() => handlePreset(preset)}
          >
            {preset.label}
          </Button>
        ))}
      </div>
    </div>
  );
}

export default DateRangeFilter;
