/**
 * AlertCoverageLayer Tests
 *
 * Tests for the alert coverage visualization component including:
 * - Loading skeleton
 * - Empty data message
 * - Summary stats rendering
 * - Channel breakdown
 * - Barangay delivery bars with color coding
 * - Custom hours parameter
 */

import { AlertCoverageLayer } from "@/features/alerts/components/AlertCoverageLayer";
import { render, screen, waitFor } from "@/test/utils";
import { server } from "@/tests/mocks/server";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

// ---------------------------------------------------------------------------
// MSW Handlers
// ---------------------------------------------------------------------------

function mockCoverageHandler(data: Record<string, unknown> = {}, status = 200) {
  return http.get("*/api/v1/alerts/coverage", () => {
    return HttpResponse.json(
      {
        success: true,
        coverage: {
          hours: 24,
          total_alerts: 150,
          total_delivered: 142,
          total_failed: 3,
          total_pending: 5,
          delivery_rate_pct: 94.7,
          median_delivery_seconds: 28.5,
        },
        barangays: {
          Baclaran: {
            delivered: 43,
            failed: 0,
            pending: 2,
            partial: 0,
            total: 45,
            delivery_pct: 95.6,
            risk_levels: { 0: 10, 1: 30, 2: 5 },
          },
          "San Dionisio": {
            delivered: 18,
            failed: 2,
            pending: 0,
            partial: 0,
            total: 20,
            delivery_pct: 40.0,
            risk_levels: { 0: 5, 1: 10, 2: 5 },
          },
          "BF Homes": {
            delivered: 25,
            failed: 0,
            pending: 0,
            partial: 0,
            total: 25,
            delivery_pct: 65.0,
            risk_levels: { 0: 10, 1: 10, 2: 5 },
          },
        },
        channels: {
          web: { delivered: 95, failed: 2, pending: 3, total: 100 },
          sms: { delivered: 28, failed: 1, pending: 1, total: 30 },
        },
        ...data,
      },
      { status },
    );
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AlertCoverageLayer", () => {
  describe("Loading state", () => {
    it("shows loading skeleton", () => {
      // Don't set a handler → request will be pending
      server.use(
        http.get("*/api/v1/alerts/coverage", async () => {
          await new Promise(() => {}); // Never resolves
        }),
      );

      const { container } = render(<AlertCoverageLayer />);
      expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
    });
  });

  describe("Empty data", () => {
    it("shows empty message when no barangays", async () => {
      server.use(
        mockCoverageHandler({
          coverage: {
            hours: 24,
            total_alerts: 0,
            total_delivered: 0,
            total_failed: 0,
            total_pending: 0,
            delivery_rate_pct: 0,
            median_delivery_seconds: null,
          },
          barangays: {},
          channels: {},
        }),
      );

      render(<AlertCoverageLayer />);

      await waitFor(() => {
        expect(screen.getByText(/No alert coverage data/)).toBeInTheDocument();
      });
    });
  });

  describe("Summary stats", () => {
    it("renders total alerts", async () => {
      server.use(mockCoverageHandler());
      render(<AlertCoverageLayer />);

      await waitFor(() => {
        expect(screen.getByText("Total Alerts")).toBeInTheDocument();
        expect(screen.getByText("150")).toBeInTheDocument();
      });
    });

    it("renders delivery rate", async () => {
      server.use(mockCoverageHandler());
      render(<AlertCoverageLayer />);

      await waitFor(() => {
        expect(screen.getByText("Delivery Rate")).toBeInTheDocument();
        expect(screen.getByText("94.7%")).toBeInTheDocument();
      });
    });

    it("renders median delivery time", async () => {
      server.use(mockCoverageHandler());
      render(<AlertCoverageLayer />);

      await waitFor(() => {
        expect(screen.getByText("Median Delivery")).toBeInTheDocument();
        expect(screen.getByText("28.5s")).toBeInTheDocument();
      });
    });

    it("renders failed count", async () => {
      server.use(mockCoverageHandler());
      render(<AlertCoverageLayer />);

      await waitFor(() => {
        expect(screen.getByText("Failed")).toBeInTheDocument();
        expect(screen.getByText("3")).toBeInTheDocument();
      });
    });

    it("shows N/A when median is null", async () => {
      server.use(
        mockCoverageHandler({
          coverage: {
            hours: 24,
            total_alerts: 10,
            total_delivered: 8,
            total_failed: 2,
            total_pending: 0,
            delivery_rate_pct: 80,
            median_delivery_seconds: null,
          },
          barangays: {
            Baclaran: {
              delivered: 8,
              failed: 2,
              pending: 0,
              partial: 0,
              total: 10,
              delivery_pct: 80,
              risk_levels: {},
            },
          },
        }),
      );

      render(<AlertCoverageLayer />);

      await waitFor(() => {
        expect(screen.getByText("N/A")).toBeInTheDocument();
      });
    });
  });

  describe("Channel breakdown", () => {
    it("shows per-channel delivery percentage", async () => {
      server.use(mockCoverageHandler());
      render(<AlertCoverageLayer />);

      await waitFor(() => {
        expect(screen.getByText(/web/i)).toBeInTheDocument();
        expect(screen.getByText(/sms/i)).toBeInTheDocument();
      });
    });
  });

  describe("Barangay coverage bars", () => {
    it("shows all barangay names", async () => {
      server.use(mockCoverageHandler());
      render(<AlertCoverageLayer />);

      await waitFor(() => {
        expect(screen.getByText("Baclaran")).toBeInTheDocument();
        expect(screen.getByText("San Dionisio")).toBeInTheDocument();
        expect(screen.getByText("BF Homes")).toBeInTheDocument();
      });
    });

    it("shows delivery percentages", async () => {
      server.use(mockCoverageHandler());
      render(<AlertCoverageLayer />);

      await waitFor(() => {
        expect(screen.getByText("95.6%")).toBeInTheDocument();
        expect(screen.getByText("40%")).toBeInTheDocument();
        expect(screen.getByText("65%")).toBeInTheDocument();
      });
    });

    it("sorts barangays by delivery_pct ascending", async () => {
      server.use(mockCoverageHandler());
      render(<AlertCoverageLayer />);

      await waitFor(() => {
        const names = screen.getAllByText(/Baclaran|San Dionisio|BF Homes/);
        // San Dionisio (40%) should come first, then BF Homes (65%), then Baclaran (95.6%)
        expect(names[0]!.textContent).toBe("San Dionisio");
        expect(names[1]!.textContent).toBe("BF Homes");
        expect(names[2]!.textContent).toBe("Baclaran");
      });
    });

    it("shows correct delivery labels", async () => {
      server.use(mockCoverageHandler());
      render(<AlertCoverageLayer />);

      await waitFor(() => {
        // Baclaran: 95.6% → "Good"
        expect(screen.getByText("Good")).toBeInTheDocument();
        // BF Homes: 65% → "Moderate"
        expect(screen.getByText("Moderate")).toBeInTheDocument();
        // San Dionisio: 40% → "Low"
        expect(screen.getByText("Low")).toBeInTheDocument();
      });
    });
  });

  describe("Custom hours", () => {
    it("passes custom hours to hook", async () => {
      let requestedHours: string | null = null;
      server.use(
        http.get("*/api/v1/alerts/coverage", ({ request }) => {
          const url = new URL(request.url);
          requestedHours = url.searchParams.get("hours");
          return HttpResponse.json({
            success: true,
            coverage: {
              hours: 48,
              total_alerts: 0,
              total_delivered: 0,
              total_failed: 0,
              total_pending: 0,
              delivery_rate_pct: 0,
              median_delivery_seconds: null,
            },
            barangays: {},
            channels: {},
          });
        }),
      );

      render(<AlertCoverageLayer hours={48} />);

      await waitFor(() => {
        expect(requestedHours).toBe("48");
      });
    });
  });
});
