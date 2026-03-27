/**
 * TimelineScrubber – interactive playback control for historical prediction data.
 *
 * Displays a horizontal time axis. Users can scrub to any point, or press Play
 * to auto-advance through the timeline. The parent receives the index of the
 * currently-highlighted record via `onIndexChange`.
 */

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { format } from "date-fns";
import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

export interface TimelineItem {
  /** ISO timestamp */
  timestamp: string;
  /** Risk label for colouring the tick */
  risk_label?: string;
}

interface TimelineScrubberProps {
  /** Ordered array of timeline items (oldest → newest) */
  items: TimelineItem[];
  /** Currently selected index */
  index: number;
  /** Called when the user scrubs or playback advances */
  onIndexChange: (index: number) => void;
  /** Playback speed in milliseconds per step (default: 800) */
  speed?: number;
  className?: string;
}

const RISK_TICK_COLORS: Record<string, string> = {
  Safe: "bg-emerald-500",
  Low: "bg-emerald-500",
  Alert: "bg-amber-500",
  Moderate: "bg-amber-500",
  Critical: "bg-red-500",
  High: "bg-red-500",
};

export function TimelineScrubber({
  items,
  index,
  onIndexChange,
  speed = 800,
  className,
}: TimelineScrubberProps) {
  const [playing, setPlaying] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const count = items.length;

  // Stop playback when reaching the end
  const stopPlayback = useCallback(() => {
    setPlaying(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Playback loop
  useEffect(() => {
    if (!playing) return;
    intervalRef.current = setInterval(() => {
      onIndexChange(
        // This is read via a functional-style updater to avoid stale closures
        // but since onIndexChange is a setter we rely on the parent's state:
        index + 1 < count ? index + 1 : index,
      );
    }, speed);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, speed, index, count, onIndexChange]);

  // Auto-stop at end
  useEffect(() => {
    if (playing && index >= count - 1) {
      stopPlayback();
    }
  }, [playing, index, count, stopPlayback]);

  const togglePlay = () => {
    if (playing) {
      stopPlayback();
    } else {
      // If at end, restart from beginning
      if (index >= count - 1) onIndexChange(0);
      setPlaying(true);
    }
  };

  if (count === 0) return null;

  const currentItem = items[index];
  const startDate = items[0]?.timestamp;
  const endDate = items[count - 1]?.timestamp;

  return (
    <div className={cn("space-y-3", className)}>
      {/* Controls row */}
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => onIndexChange(0)}
          disabled={index === 0}
          aria-label="Skip to start"
        >
          <SkipBack className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={togglePlay}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => onIndexChange(count - 1)}
          disabled={index >= count - 1}
          aria-label="Skip to end"
        >
          <SkipForward className="h-4 w-4" />
        </Button>

        {/* Current time label */}
        <span className="text-sm font-medium tabular-nums ml-2">
          {currentItem
            ? format(new Date(currentItem.timestamp), "MMM dd, yyyy HH:mm")
            : "—"}
        </span>
        <span className="text-xs text-muted-foreground ml-auto">
          {index + 1} / {count}
        </span>
      </div>

      {/* Scrubber track */}
      <div className="relative">
        <input
          type="range"
          min={0}
          max={count - 1}
          value={index}
          onChange={(e) => {
            stopPlayback();
            onIndexChange(parseInt(e.target.value, 10));
          }}
          className="w-full accent-primary h-2 rounded-lg cursor-pointer"
          aria-label="Timeline scrubber"
        />

        {/* Risk-colored tick marks (show up to 60 ticks) */}
        {count <= 60 && (
          <div className="flex justify-between px-px mt-1" aria-hidden>
            {items.map((item, i) => (
              <div
                key={i}
                className={cn(
                  "w-1.5 h-1.5 rounded-full transition-all",
                  RISK_TICK_COLORS[item.risk_label ?? "Safe"] ??
                    "bg-muted-foreground",
                  i === index && "ring-2 ring-primary ring-offset-1 scale-150",
                )}
                title={`${format(new Date(item.timestamp), "HH:mm")} – ${item.risk_label ?? "Unknown"}`}
              />
            ))}
          </div>
        )}

        {/* Date range labels */}
        <div className="flex justify-between text-xs text-muted-foreground mt-2">
          <span>{startDate ? format(new Date(startDate), "MMM dd") : ""}</span>
          <span>{endDate ? format(new Date(endDate), "MMM dd") : ""}</span>
        </div>
      </div>
    </div>
  );
}
