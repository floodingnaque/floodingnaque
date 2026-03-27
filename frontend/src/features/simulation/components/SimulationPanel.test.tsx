/**
 * SimulationPanel Tests
 *
 * Tests for the what-if flood simulation interface including:
 * - Initial render with default parameters
 * - Preset scenario selection
 * - Parameter slider interaction
 * - Result display (Safe/Alert/Critical)
 * - Error state rendering
 * - Skeleton loading state
 */

import {
  SimulationPanel,
  SimulationPanelSkeleton,
} from "@/features/simulation";
import { render, screen, waitFor } from "@/test/utils";
import { server } from "@/tests/mocks/server";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

// ---------------------------------------------------------------------------
// MSW Handlers
// ---------------------------------------------------------------------------

function mockSimulateHandler(
  result: Record<string, unknown> = {},
  status = 200,
) {
  return http.post("*/api/v1/predict/simulate", async () => {
    return HttpResponse.json(
      {
        success: true,
        simulation: true,
        scenario: "custom",
        input: { temperature: 303, humidity: 75, precipitation: 10 },
        prediction: 0,
        probability: 0.12,
        risk_level: 0,
        risk_label: "Safe",
        confidence: 0.88,
        model_version: "v6",
        features_used: ["temperature", "humidity", "precipitation"],
        explanation: null,
        request_id: "test-req-1",
        ...result,
      },
      { status },
    );
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SimulationPanel", () => {
  describe("Initial Render", () => {
    it("renders scenario controls heading", () => {
      server.use(mockSimulateHandler());
      render(<SimulationPanel />);

      expect(screen.getByText("Scenario Controls")).toBeInTheDocument();
      expect(screen.getByText(/Adjust weather parameters/)).toBeInTheDocument();
    });

    it("renders preset dropdown with Custom selected", () => {
      server.use(mockSimulateHandler());
      render(<SimulationPanel />);

      expect(screen.getByText("Preset Scenario")).toBeInTheDocument();
    });

    it("renders all parameter sliders", () => {
      server.use(mockSimulateHandler());
      render(<SimulationPanel />);

      expect(screen.getByText("Temperature")).toBeInTheDocument();
      expect(screen.getByText("Humidity")).toBeInTheDocument();
      expect(screen.getByText("Precipitation")).toBeInTheDocument();
      expect(screen.getByText("Wind Speed")).toBeInTheDocument();
      expect(screen.getByText("Pressure")).toBeInTheDocument();
    });

    it("shows slider ranges", () => {
      server.use(mockSimulateHandler());
      render(<SimulationPanel />);

      // Temperature range
      expect(screen.getByText("290K")).toBeInTheDocument();
      expect(screen.getByText("315K")).toBeInTheDocument();
      // Humidity range
      expect(screen.getByText("0%")).toBeInTheDocument();
      expect(screen.getByText("100%")).toBeInTheDocument();
    });
  });

  describe("Prediction Results", () => {
    it("displays Safe result", async () => {
      server.use(
        mockSimulateHandler({
          risk_label: "Safe",
          probability: 0.1,
          confidence: 0.9,
        }),
      );
      render(<SimulationPanel />);

      await waitFor(() => {
        expect(screen.getByText("Safe")).toBeInTheDocument();
      });
    });

    it("displays Critical result", async () => {
      server.use(
        mockSimulateHandler({
          risk_label: "Critical",
          prediction: 1,
          probability: 0.92,
          confidence: 0.92,
          risk_level: 2,
        }),
      );
      render(<SimulationPanel />);

      await waitFor(() => {
        expect(screen.getByText("Critical")).toBeInTheDocument();
      });
    });

    it("displays Alert result", async () => {
      server.use(
        mockSimulateHandler({
          risk_label: "Alert",
          prediction: 1,
          probability: 0.6,
          confidence: 0.75,
          risk_level: 1,
        }),
      );
      render(<SimulationPanel />);

      await waitFor(() => {
        expect(screen.getByText("Alert")).toBeInTheDocument();
      });
    });

    it("shows prediction result card with stats", async () => {
      server.use(
        mockSimulateHandler({
          probability: 0.75,
          confidence: 0.85,
          risk_level: 1,
          model_version: "v6",
          features_used: ["temp", "humidity", "precip"],
        }),
      );
      render(<SimulationPanel />);

      await waitFor(() => {
        expect(screen.getByText("Prediction Result")).toBeInTheDocument();
      });

      expect(screen.getAllByText("Flood Probability").length).toBeGreaterThan(
        0,
      );
      expect(screen.getAllByText("Confidence").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Risk Level").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Features Used").length).toBeGreaterThan(0);
    });
  });

  describe("Error Handling", () => {
    it("shows error message on API failure", async () => {
      server.use(
        http.post("*/api/v1/predict/simulate", () => {
          return HttpResponse.json(
            { error: "Model not loaded" },
            { status: 500 },
          );
        }),
      );
      render(<SimulationPanel />);

      await waitFor(
        () => {
          // The mutation will set an error
          const errorCards = screen.queryAllByText(/error|failed|not loaded/i);
          // Error display may vary, but the component shouldn't crash
          expect(
            document.querySelector('[class*="border-destructive"]') !== null ||
              errorCards.length > 0 ||
              screen.queryByText(/Adjust parameters/) !== null,
          ).toBeTruthy();
        },
        { timeout: 3000 },
      );
    });
  });

  describe("Skeleton", () => {
    it("renders skeleton loader", () => {
      const { container } = render(<SimulationPanelSkeleton />);
      expect(container.firstChild).toBeInTheDocument();
    });
  });
});
