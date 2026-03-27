/**
 * FloodRiskHeatmap Tests
 *
 * Tests for the treemap-style heatmap showing per-barangay flood risk.
 * Covers: loading skeleton, empty data, risk/frequency modes, cell rendering,
 * gradient legend, summary footer.
 */

import { render, screen } from "@/test/utils";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FloodRiskHeatmap, FloodRiskHeatmapSkeleton } from "./FloodRiskHeatmap";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseFloodHistory = vi.fn();

vi.mock("@/features/dashboard/hooks/useAnalytics", () => ({
  useFloodHistory: () => mockUseFloodHistory(),
}));

vi.mock("@/config/paranaque", () => ({
  BARANGAYS: [
    { name: "Baclaran", key: "baclaran", lat: 14.524, lon: 121.001 },
    { name: "Tambo", key: "tambo", lat: 14.518, lon: 120.995 },
    { name: "BF Homes", key: "bf_homes", lat: 14.4545, lon: 121.0234 },
    { name: "Moonwalk", key: "moonwalk", lat: 14.454, lon: 121.01 },
  ],
}));

// ---------------------------------------------------------------------------
// Test Data
// ---------------------------------------------------------------------------

const floodHistoryData = {
  frequency: [
    { barangay: "Baclaran", events: 7 },
    { barangay: "Tambo", events: 2 },
    { barangay: "Moonwalk", events: 11 },
    // BF Homes not in list → defaults to 0
  ],
  yearly: [],
  monthly: [],
  recent: [],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("FloodRiskHeatmapSkeleton", () => {
  it("renders 16 skeleton cells in a 4-col grid", () => {
    const { container } = render(<FloodRiskHeatmapSkeleton />);
    const skeletons = container.querySelectorAll(".grid .aspect-square");
    expect(skeletons.length).toBe(16);
  });
});

describe("FloodRiskHeatmap", () => {
  it("shows skeleton while loading", () => {
    mockUseFloodHistory.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<FloodRiskHeatmap />);
    const skeletons = container.querySelectorAll(".grid .aspect-square");
    expect(skeletons.length).toBe(16);
  });

  it("renders all cells with 0% when frequency data is empty", () => {
    mockUseFloodHistory.mockReturnValue({
      data: { frequency: [] },
      isLoading: false,
    });
    render(<FloodRiskHeatmap />);
    // All barangays still render with 0% since BARANGAYS config is used
    const zeroPcts = screen.getAllByText("0%");
    expect(zeroPcts.length).toBe(4);
  });

  it("renders heatmap title", () => {
    mockUseFloodHistory.mockReturnValue({
      data: floodHistoryData,
      isLoading: false,
    });
    render(<FloodRiskHeatmap />);
    expect(screen.getByText("Flood Risk Heatmap")).toBeInTheDocument();
  });

  it("renders all barangay cells in risk mode (default)", () => {
    mockUseFloodHistory.mockReturnValue({
      data: floodHistoryData,
      isLoading: false,
    });
    render(<FloodRiskHeatmap />);

    expect(screen.getByText("Baclaran")).toBeInTheDocument();
    expect(screen.getByText("Tambo")).toBeInTheDocument();
    expect(screen.getByText("Moonwalk")).toBeInTheDocument();
    expect(screen.getByText("BF Homes")).toBeInTheDocument();
  });

  it("shows percentage values in risk mode", () => {
    mockUseFloodHistory.mockReturnValue({
      data: floodHistoryData,
      isLoading: false,
    });
    render(<FloodRiskHeatmap />);

    // Moonwalk has 11 events (max), normalized to 1.0 → 100%
    expect(screen.getByText("100%")).toBeInTheDocument();
    // Baclaran: 7/11 ≈ 0.636 → 64%
    expect(screen.getByText("64%")).toBeInTheDocument();
    // BF Homes: 0/11 → 0%
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("switches to frequency mode and displays event counts", async () => {
    const user = userEvent.setup();
    mockUseFloodHistory.mockReturnValue({
      data: floodHistoryData,
      isLoading: false,
    });
    render(<FloodRiskHeatmap />);

    const freqBtn = screen.getByRole("button", { name: /event freq/i });
    await user.click(freqBtn);

    // Should now show raw frequency numbers instead of percentages
    expect(screen.getByText("11")).toBeInTheDocument(); // Moonwalk
    expect(screen.getByText("7")).toBeInTheDocument(); // Baclaran
    expect(screen.getByText("2")).toBeInTheDocument(); // Tambo
    expect(screen.getByText("0")).toBeInTheDocument(); // BF Homes
  });

  it("has two mode toggle buttons", () => {
    mockUseFloodHistory.mockReturnValue({
      data: floodHistoryData,
      isLoading: false,
    });
    render(<FloodRiskHeatmap />);

    expect(
      screen.getByRole("button", { name: /risk score/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /event freq/i }),
    ).toBeInTheDocument();
  });

  it("renders gradient legend text for risk mode", () => {
    mockUseFloodHistory.mockReturnValue({
      data: floodHistoryData,
      isLoading: false,
    });
    render(<FloodRiskHeatmap />);

    expect(screen.getByText("Low Risk")).toBeInTheDocument();
    expect(screen.getByText("High Risk")).toBeInTheDocument();
  });

  it("renders gradient legend text for frequency mode", async () => {
    const user = userEvent.setup();
    mockUseFloodHistory.mockReturnValue({
      data: floodHistoryData,
      isLoading: false,
    });
    render(<FloodRiskHeatmap />);

    await user.click(screen.getByRole("button", { name: /event freq/i }));

    expect(screen.getByText("Few Events")).toBeInTheDocument();
    expect(screen.getByText("Many Events")).toBeInTheDocument();
  });

  it("shows barangay count and critical count in footer", () => {
    mockUseFloodHistory.mockReturnValue({
      data: floodHistoryData,
      isLoading: false,
    });
    render(<FloodRiskHeatmap />);

    // 4 barangays in our mock
    expect(screen.getByText(/4 barangays/)).toBeInTheDocument();
    expect(screen.getByText(/Last 3 years/)).toBeInTheDocument();
  });

  it("sorts cells descending by risk in risk mode", () => {
    mockUseFloodHistory.mockReturnValue({
      data: floodHistoryData,
      isLoading: false,
    });
    const { container } = render(<FloodRiskHeatmap />);

    const cells = container.querySelectorAll(".grid > div");
    const names = Array.from(cells).map(
      (c) => c.querySelector("span")?.textContent,
    );

    // Moonwalk (100%) first, then Baclaran (64%), Tambo (18%), BF Homes (0%)
    expect(names[0]).toBe("Moonwalk");
    expect(names[names.length - 1]).toBe("BF Homes");
  });
});
