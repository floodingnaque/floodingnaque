/**
 * TimelineScrubber Tests
 *
 * Tests for the interactive timeline playback component including:
 * - Control button rendering and state
 * - Playback start/stop
 * - Skip to start/end navigation
 * - Risk-colored tick mark rendering
 * - Empty timeline handling
 * - Date range label display
 */

import type { TimelineItem } from "@/features/predictions/components/TimelineScrubber";
import { TimelineScrubber } from "@/features/predictions/components/TimelineScrubber";
import { render, screen } from "@/test/utils";
import { describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function createTimelineItems(count: number): TimelineItem[] {
  const base = new Date("2026-01-15T00:00:00Z");
  return Array.from({ length: count }, (_, i) => ({
    timestamp: new Date(base.getTime() + i * 3600_000).toISOString(),
    risk_label: i % 3 === 0 ? "Safe" : i % 3 === 1 ? "Alert" : "Critical",
  }));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("TimelineScrubber", () => {
  describe("Empty timeline", () => {
    it("renders nothing when items array is empty", () => {
      const { container } = render(
        <TimelineScrubber items={[]} index={0} onIndexChange={vi.fn()} />,
      );
      expect(container.firstChild).toBeNull();
    });
  });

  describe("Control buttons", () => {
    it("renders play, skip-back, and skip-forward buttons", () => {
      render(
        <TimelineScrubber
          items={createTimelineItems(10)}
          index={5}
          onIndexChange={vi.fn()}
        />,
      );

      expect(screen.getByLabelText("Play")).toBeInTheDocument();
      expect(screen.getByLabelText("Skip to start")).toBeInTheDocument();
      expect(screen.getByLabelText("Skip to end")).toBeInTheDocument();
    });

    it("disables skip-back when at index 0", () => {
      render(
        <TimelineScrubber
          items={createTimelineItems(10)}
          index={0}
          onIndexChange={vi.fn()}
        />,
      );

      expect(screen.getByLabelText("Skip to start")).toBeDisabled();
    });

    it("disables skip-forward when at last index", () => {
      const items = createTimelineItems(10);
      render(
        <TimelineScrubber
          items={items}
          index={items.length - 1}
          onIndexChange={vi.fn()}
        />,
      );

      expect(screen.getByLabelText("Skip to end")).toBeDisabled();
    });
  });

  describe("Navigation", () => {
    it("skip-back calls onIndexChange with 0", async () => {
      const onIndexChange = vi.fn();
      const { user } = render(
        <TimelineScrubber
          items={createTimelineItems(10)}
          index={5}
          onIndexChange={onIndexChange}
        />,
      );

      await user.click(screen.getByLabelText("Skip to start"));
      expect(onIndexChange).toHaveBeenCalledWith(0);
    });

    it("skip-forward calls onIndexChange with last index", async () => {
      const onIndexChange = vi.fn();
      const items = createTimelineItems(10);
      const { user } = render(
        <TimelineScrubber
          items={items}
          index={5}
          onIndexChange={onIndexChange}
        />,
      );

      await user.click(screen.getByLabelText("Skip to end"));
      expect(onIndexChange).toHaveBeenCalledWith(items.length - 1);
    });
  });

  describe("Index counter", () => {
    it("shows current position out of total", () => {
      render(
        <TimelineScrubber
          items={createTimelineItems(50)}
          index={25}
          onIndexChange={vi.fn()}
        />,
      );

      expect(screen.getByText("26 / 50")).toBeInTheDocument();
    });
  });

  describe("Date display", () => {
    it("shows formatted current timestamp", () => {
      const items: TimelineItem[] = [
        { timestamp: "2026-03-15T14:30:00Z", risk_label: "Safe" },
        { timestamp: "2026-03-15T15:30:00Z", risk_label: "Alert" },
        { timestamp: "2026-03-15T16:30:00Z", risk_label: "Critical" },
      ];

      render(
        <TimelineScrubber items={items} index={0} onIndexChange={vi.fn()} />,
      );

      // The current item's formatted timestamp should appear
      // Format is "MMM dd, yyyy HH:mm" — date-fns uses local timezone
      expect(screen.getByText(/Mar 15, 2026/)).toBeInTheDocument();
    });
  });

  describe("Scrubber input", () => {
    it("renders the range input", () => {
      render(
        <TimelineScrubber
          items={createTimelineItems(10)}
          index={3}
          onIndexChange={vi.fn()}
        />,
      );

      const slider = screen.getByLabelText("Timeline scrubber");
      expect(slider).toBeInTheDocument();
      expect(slider).toHaveAttribute("type", "range");
      expect(slider).toHaveAttribute("min", "0");
      expect(slider).toHaveAttribute("max", "9");
    });
  });

  describe("Risk tick marks", () => {
    it("renders tick marks for small timelines (<=60 items)", () => {
      const items = createTimelineItems(10);
      const { container } = render(
        <TimelineScrubber items={items} index={0} onIndexChange={vi.fn()} />,
      );

      // Each item gets a tick mark div with rounded-full class
      const ticks = container.querySelectorAll(".rounded-full.w-1\\.5");
      expect(ticks.length).toBe(10);
    });

    it("hides tick marks for large timelines (>60 items)", () => {
      const items = createTimelineItems(100);
      const { container } = render(
        <TimelineScrubber items={items} index={0} onIndexChange={vi.fn()} />,
      );

      // Should not render individual tick marks
      const ticks = container.querySelectorAll(".rounded-full.w-1\\.5");
      expect(ticks.length).toBe(0);
    });
  });

  describe("Playback", () => {
    it("shows Pause label when playing", async () => {
      const { user } = render(
        <TimelineScrubber
          items={createTimelineItems(10)}
          index={0}
          onIndexChange={vi.fn()}
        />,
      );

      await user.click(screen.getByLabelText("Play"));
      expect(screen.getByLabelText("Pause")).toBeInTheDocument();
    });
  });
});
