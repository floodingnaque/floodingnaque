/**
 * Worker Manager - Singleton lazy-loader for all Web Workers.
 *
 * Uses comlink to wrap each worker in a type-safe async proxy.
 * Workers are created lazily on first access and reused across the app.
 *
 * @example
 * ```ts
 * import { getChartWorker, getRiskWorker } from '@/lib/workers';
 *
 * const chart = await getChartWorker();
 * const downsampled = await chart.downsample(data, 200);
 * ```
 */

import type { ChartWorkerApi } from "@/workers/chart-worker";
import type { GeoWorkerApi } from "@/workers/geo-worker";
import type { RiskWorkerApi } from "@/workers/risk-worker";
import type { StatsWorkerApi } from "@/workers/stats-worker";
import type { ValidationWorkerApi } from "@/workers/validation-worker";
import { wrap, type Remote } from "comlink";

// Singleton proxies - created lazily
let chartProxy: Remote<ChartWorkerApi> | null = null;
let geoProxy: Remote<GeoWorkerApi> | null = null;
let riskProxy: Remote<RiskWorkerApi> | null = null;
let statsProxy: Remote<StatsWorkerApi> | null = null;
let validationProxy: Remote<ValidationWorkerApi> | null = null;

export function getChartWorker(): Remote<ChartWorkerApi> {
  if (!chartProxy) {
    const worker = new Worker(
      new URL("@/workers/chart-worker.ts", import.meta.url),
      { type: "module" },
    );
    chartProxy = wrap<ChartWorkerApi>(worker);
  }
  return chartProxy;
}

export function getGeoWorker(): Remote<GeoWorkerApi> {
  if (!geoProxy) {
    const worker = new Worker(
      new URL("@/workers/geo-worker.ts", import.meta.url),
      { type: "module" },
    );
    geoProxy = wrap<GeoWorkerApi>(worker);
  }
  return geoProxy;
}

export function getRiskWorker(): Remote<RiskWorkerApi> {
  if (!riskProxy) {
    const worker = new Worker(
      new URL("@/workers/risk-worker.ts", import.meta.url),
      { type: "module" },
    );
    riskProxy = wrap<RiskWorkerApi>(worker);
  }
  return riskProxy;
}

export function getStatsWorker(): Remote<StatsWorkerApi> {
  if (!statsProxy) {
    const worker = new Worker(
      new URL("@/workers/stats-worker.ts", import.meta.url),
      { type: "module" },
    );
    statsProxy = wrap<StatsWorkerApi>(worker);
  }
  return statsProxy;
}

export function getValidationWorker(): Remote<ValidationWorkerApi> {
  if (!validationProxy) {
    const worker = new Worker(
      new URL("@/workers/validation-worker.ts", import.meta.url),
      { type: "module" },
    );
    validationProxy = wrap<ValidationWorkerApi>(worker);
  }
  return validationProxy;
}

/**
 * Terminate all active workers. Useful for cleanup on app shutdown
 * or hot-module replacement in development.
 */
export function terminateAllWorkers(): void {
  chartProxy = null;
  geoProxy = null;
  riskProxy = null;
  statsProxy = null;
  validationProxy = null;
}
