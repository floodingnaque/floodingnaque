/**
 * useSimulation Hook Tests
 *
 * Tests for the simulation TanStack Query mutation hook including:
 * - Successful mutation call
 * - Error handling
 * - Query key factory
 */

import { simulationKeys, useSimulation } from "@/features/simulation";
import { createWrapper } from "@/test/utils";
import { server } from "@/tests/mocks/server";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

const mockResponse = {
  success: true,
  simulation: true,
  scenario: "custom",
  input: { temperature: 303, humidity: 75, precipitation: 10 },
  prediction: 0,
  probability: 0.15,
  risk_level: 0,
  risk_label: "Safe",
  confidence: 0.85,
  model_version: "v6",
  features_used: ["temperature", "humidity", "precipitation"],
  request_id: "test-1",
};

describe("useSimulation", () => {
  it("starts idle", () => {
    server.use(
      http.post("*/api/v1/predict/simulate", () =>
        HttpResponse.json(mockResponse),
      ),
    );

    const { result } = renderHook(() => useSimulation(), {
      wrapper: createWrapper(),
    });

    expect(result.current.status).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  it("returns prediction on successful mutation", async () => {
    server.use(
      http.post("*/api/v1/predict/simulate", () =>
        HttpResponse.json(mockResponse),
      ),
    );

    const { result } = renderHook(() => useSimulation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      temperature: 303,
      humidity: 75,
      precipitation: 10,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.risk_label).toBe("Safe");
    expect(result.current.data?.probability).toBe(0.15);
  });

  it("sets error on API failure", async () => {
    server.use(
      http.post("*/api/v1/predict/simulate", () =>
        HttpResponse.json({ error: "Model not found" }, { status: 404 }),
      ),
    );

    const { result } = renderHook(() => useSimulation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      temperature: 300,
      humidity: 80,
      precipitation: 50,
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe("simulationKeys", () => {
  it("returns base key", () => {
    expect(simulationKeys.all).toEqual(["simulation"]);
  });

  it("returns run key with params", () => {
    const params = { temperature: 300, humidity: 80, precipitation: 50 };
    expect(simulationKeys.run(params)).toEqual(["simulation", "run", params]);
  });
});
