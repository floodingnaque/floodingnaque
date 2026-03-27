/**
 * ExplainabilityPanel Tests
 *
 * Tests for the XAI visualization panel including:
 * - WhyAlertCard rendering for each risk level
 * - FeatureImportanceChart bar count
 * - ContributionChart waterfall rendering
 * - Empty/null explanation handling
 * - Smart alert factors rendering
 */

import { ExplainabilityPanel } from "@/features/flooding/components/ExplainabilityPanel";
import { render, screen } from "@/test/utils";
import type { RiskLevel, XAIExplanation } from "@/types";
import { describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mock recharts to avoid ResizeObserver constructor issues in jsdom
// ---------------------------------------------------------------------------
vi.mock("recharts", async () => {
  const React = await import("react");
  return {
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) =>
      React.createElement(
        "div",
        { "data-testid": "responsive-container" },
        children,
      ),
    BarChart: ({ children }: { children: React.ReactNode }) =>
      React.createElement("div", { "data-testid": "bar-chart" }, children),
    Bar: () => React.createElement("div"),
    CartesianGrid: () => React.createElement("div"),
    Cell: () => React.createElement("div"),
    ReferenceLine: () => React.createElement("div"),
    Tooltip: () => React.createElement("div"),
    XAxis: () => React.createElement("div"),
    YAxis: () => React.createElement("div"),
  };
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function createExplanation(
  overrides: Partial<XAIExplanation> = {},
): XAIExplanation {
  return {
    global_feature_importances: [
      { feature: "precipitation", label: "Precipitation", importance: 0.35 },
      { feature: "humidity", label: "Humidity", importance: 0.25 },
      { feature: "temperature", label: "Temperature", importance: 0.15 },
      { feature: "wind_speed", label: "Wind Speed", importance: 0.1 },
      { feature: "pressure", label: "Pressure", importance: 0.08 },
      { feature: "month", label: "Month", importance: 0.07 },
    ],
    prediction_contributions: [
      {
        feature: "precipitation",
        label: "Precipitation",
        contribution: 0.25,
        abs_contribution: 0.25,
        direction: "increases_risk",
      },
      {
        feature: "humidity",
        label: "Humidity",
        contribution: 0.15,
        abs_contribution: 0.15,
        direction: "increases_risk",
      },
      {
        feature: "temperature",
        label: "Temperature",
        contribution: -0.05,
        abs_contribution: 0.05,
        direction: "decreases_risk",
      },
    ],
    why_alert: {
      summary:
        "Critical due to heavy rainfall (80 mm) + high humidity (92%) (87% confidence).",
      risk_label: "Critical",
      confidence_pct: 87,
      factors: [
        { text: "heavy rainfall (80 mm)", severity: "high" },
        { text: "high humidity (92%)", severity: "medium" },
        {
          text: "High moisture saturation with active rainfall",
          severity: "high",
        },
      ],
    },
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ExplainabilityPanel", () => {
  describe("Null/Empty handling", () => {
    it("returns null when explanation and smartAlertFactors are absent", () => {
      const { container } = render(
        <ExplainabilityPanel riskLevel={0} explanation={null} />,
      );
      expect(container.firstChild).toBeNull();
    });

    it("returns null when explanation is undefined and no smart factors", () => {
      const { container } = render(<ExplainabilityPanel riskLevel={1} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe("WhyAlertCard", () => {
    it("renders the summary text", () => {
      const explanation = createExplanation();
      render(<ExplainabilityPanel riskLevel={2} explanation={explanation} />);

      expect(
        screen.getByText(/Critical due to heavy rainfall/),
      ).toBeInTheDocument();
    });

    it("renders section heading", () => {
      render(
        <ExplainabilityPanel riskLevel={1} explanation={createExplanation()} />,
      );

      expect(screen.getByText("Why This Classification?")).toBeInTheDocument();
    });

    it("renders contributing factor badges", () => {
      const explanation = createExplanation();
      render(<ExplainabilityPanel riskLevel={2} explanation={explanation} />);

      expect(screen.getByText("Contributing Factors")).toBeInTheDocument();
      expect(screen.getByText("heavy rainfall (80 mm)")).toBeInTheDocument();
      expect(screen.getByText("high humidity (92%)")).toBeInTheDocument();
      expect(
        screen.getByText("High moisture saturation with active rainfall"),
      ).toBeInTheDocument();
    });

    it("hides factor badges section when empty", () => {
      const explanation = createExplanation({
        why_alert: {
          summary: "Safe - all parameters normal.",
          risk_label: "Safe",
          confidence_pct: 95,
          factors: [],
        },
      });
      render(<ExplainabilityPanel riskLevel={0} explanation={explanation} />);

      expect(
        screen.queryByText("Contributing Factors"),
      ).not.toBeInTheDocument();
    });

    it.each([
      [0, "Safe"],
      [1, "Alert"],
      [2, "Critical"],
    ] as [RiskLevel, string][])(
      "renders correctly for risk level %i (%s)",
      (level, _label) => {
        const explanation = createExplanation({
          why_alert: {
            summary: `${_label} - test`,
            risk_label: _label,
            confidence_pct: 90,
            factors: [{ text: "test factor", severity: "low" }],
          },
        });
        render(
          <ExplainabilityPanel riskLevel={level} explanation={explanation} />,
        );

        expect(screen.getByText(`${_label} - test`)).toBeInTheDocument();
        expect(screen.getByText("test factor")).toBeInTheDocument();
      },
    );
  });

  describe("FeatureImportanceChart", () => {
    it("renders chart heading", () => {
      render(
        <ExplainabilityPanel riskLevel={1} explanation={createExplanation()} />,
      );

      expect(screen.getByText("Feature Importance")).toBeInTheDocument();
      expect(
        screen.getByText("How much each feature influences the model overall"),
      ).toBeInTheDocument();
    });

    it("does not render when importances are empty", () => {
      const explanation = createExplanation({
        global_feature_importances: [],
      });
      render(<ExplainabilityPanel riskLevel={0} explanation={explanation} />);

      expect(screen.queryByText("Feature Importance")).not.toBeInTheDocument();
    });
  });

  describe("ContributionChart", () => {
    it("renders chart heading", () => {
      render(
        <ExplainabilityPanel riskLevel={2} explanation={createExplanation()} />,
      );

      expect(screen.getByText("Prediction Contributions")).toBeInTheDocument();
      expect(
        screen.getByText(/How each feature pushed the risk score/),
      ).toBeInTheDocument();
    });

    it("renders direction legend", () => {
      render(
        <ExplainabilityPanel riskLevel={1} explanation={createExplanation()} />,
      );

      expect(screen.getByText("Increases risk")).toBeInTheDocument();
      expect(screen.getByText("Decreases risk")).toBeInTheDocument();
    });

    it("does not render when contributions are empty", () => {
      const explanation = createExplanation({
        prediction_contributions: [],
      });
      render(<ExplainabilityPanel riskLevel={0} explanation={explanation} />);

      expect(
        screen.queryByText("Prediction Contributions"),
      ).not.toBeInTheDocument();
    });
  });

  describe("SmartAlertFactors", () => {
    it("renders smart alert factors when provided", () => {
      render(
        <ExplainabilityPanel
          riskLevel={2}
          explanation={null}
          smartAlertFactors={[
            "Heavy continuous rainfall detected (≥50 mm/hr)",
            "Wind speed exceeding 25 m/s",
          ]}
        />,
      );

      expect(screen.getByText("Smart Alert Factors")).toBeInTheDocument();
      expect(
        screen.getByText("Heavy continuous rainfall detected (≥50 mm/hr)"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Wind speed exceeding 25 m/s"),
      ).toBeInTheDocument();
    });

    it("does not render smart factors section when array is empty", () => {
      render(
        <ExplainabilityPanel
          riskLevel={0}
          explanation={createExplanation()}
          smartAlertFactors={[]}
        />,
      );

      expect(screen.queryByText("Smart Alert Factors")).not.toBeInTheDocument();
    });

    it("renders both explanation and smart factors together", () => {
      render(
        <ExplainabilityPanel
          riskLevel={1}
          explanation={createExplanation()}
          smartAlertFactors={["Rising water levels detected"]}
        />,
      );

      // All sections present
      expect(screen.getByText("Why This Classification?")).toBeInTheDocument();
      expect(screen.getByText("Feature Importance")).toBeInTheDocument();
      expect(screen.getByText("Prediction Contributions")).toBeInTheDocument();
      expect(screen.getByText("Smart Alert Factors")).toBeInTheDocument();
      expect(
        screen.getByText("Rising water levels detected"),
      ).toBeInTheDocument();
    });
  });
});
