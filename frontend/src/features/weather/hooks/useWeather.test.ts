/**
 * useWeather Hook Tests
 *
 * Tests for weather data React Query hooks.
 */

import {
  useHourlyWeather,
  useWeatherData,
  useWeatherStats,
  weatherKeys,
} from "@/features/weather/hooks/useWeather";
import { createWrapper } from "@/test/utils";
import { server } from "@/tests/mocks/server";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

describe("weatherKeys", () => {
  it("should generate correct query keys", () => {
    expect(weatherKeys.all).toEqual(["weather"]);
    expect(weatherKeys.data()).toEqual(["weather", "data"]);
    expect(weatherKeys.dataList({ page: 1 })).toEqual([
      "weather",
      "data",
      { page: 1 },
    ]);
    expect(weatherKeys.hourly()).toEqual(["weather", "hourly"]);
    expect(weatherKeys.hourlyList({ days: 3 })).toEqual([
      "weather",
      "hourly",
      { days: 3 },
    ]);
    expect(weatherKeys.stats()).toEqual(["weather", "stats"]);
    expect(weatherKeys.statsByRange({ start_date: "2026-01-01" })).toEqual([
      "weather",
      "stats",
      { start_date: "2026-01-01" },
    ]);
  });
});

describe("useWeatherData", () => {
  const wrapper = createWrapper();

  it("should fetch paginated weather data successfully", async () => {
    const { result } = renderHook(
      () => useWeatherData({ page: 1, limit: 50 }),
      { wrapper },
    );

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.data).toHaveLength(50);
    expect(result.current.data?.page).toBe(1);
    expect(result.current.data?.total).toBe(1000);
  });

  it("should handle pagination correctly", async () => {
    const { result } = renderHook(
      () => useWeatherData({ page: 2, limit: 25 }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.page).toBe(2);
    expect(result.current.data?.data).toHaveLength(25);
  });

  it("should handle error state", async () => {
    server.use(
      http.get("*/api/v1/data/data", () => {
        return HttpResponse.json(
          { code: "SERVER_ERROR", message: "Database unavailable" },
          { status: 500 },
        );
      }),
    );

    const { result } = renderHook(() => useWeatherData(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeDefined();
  });

  it("should return weather data with correct structure", async () => {
    const { result } = renderHook(() => useWeatherData({ limit: 1 }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const weatherItem = result.current.data?.data[0];
    expect(weatherItem).toHaveProperty("id");
    expect(weatherItem).toHaveProperty("temperature");
    expect(weatherItem).toHaveProperty("humidity");
    expect(weatherItem).toHaveProperty("precipitation");
    expect(weatherItem).toHaveProperty("wind_speed");
    expect(weatherItem).toHaveProperty("recorded_at");
  });
});

describe("useHourlyWeather", () => {
  const wrapper = createWrapper();

  it("should fetch hourly forecast successfully", async () => {
    const { result } = renderHook(() => useHourlyWeather(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data?.length).toBeGreaterThan(0);
  });

  it("should return hourly data points", async () => {
    const { result } = renderHook(() => useHourlyWeather({ days: 1 }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(24);
  });

  it("should handle error state", async () => {
    server.use(
      http.get("*/api/v1/data/hourly", () => {
        return HttpResponse.json(
          { code: "NOT_AVAILABLE", message: "Forecast not available" },
          { status: 503 },
        );
      }),
    );

    const { result } = renderHook(() => useHourlyWeather(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useWeatherStats", () => {
  const wrapper = createWrapper();

  it("should fetch weather statistics successfully", async () => {
    const { result } = renderHook(() => useWeatherStats(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(result.current.data).toHaveProperty("avg_temperature");
    expect(result.current.data).toHaveProperty("avg_humidity");
    expect(result.current.data).toHaveProperty("total_precipitation");
    expect(result.current.data).toHaveProperty("avg_wind_speed");
    expect(result.current.data).toHaveProperty("record_count");
  });

  it("should accept date range parameters", async () => {
    const { result } = renderHook(
      () =>
        useWeatherStats({ start_date: "2026-01-01", end_date: "2026-01-31" }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeDefined();
  });

  it("should handle error state", async () => {
    server.use(
      http.get("*/api/v1/data/data", () => {
        return HttpResponse.json(
          { code: "NO_DATA", message: "No data for date range" },
          { status: 503 },
        );
      }),
    );

    const { result } = renderHook(
      () =>
        useWeatherStats({ start_date: "2020-01-01", end_date: "2020-01-31" }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useWeatherData with empty results", () => {
  const wrapper = createWrapper();

  it("should handle empty data response", async () => {
    server.use(
      http.get("*/api/v1/data/data", () => {
        return HttpResponse.json({
          success: true,
          data: [],
          total: 0,
          page: 1,
          limit: 50,
          pages: 0,
          request_id: "test-request-id",
        });
      }),
    );

    const { result } = renderHook(() => useWeatherData(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.data).toHaveLength(0);
    expect(result.current.data?.total).toBe(0);
  });
});
