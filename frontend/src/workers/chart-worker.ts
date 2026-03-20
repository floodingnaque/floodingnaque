/**
 * Chart Data Worker
 *
 * Offloads chart data transformations (aggregation, downsampling,
 * moving averages) from the main thread so Recharts renders are snappy.
 */

import { expose } from "comlink";

export interface ChartDataPoint {
  timestamp: string;
  temperature?: number;
  humidity?: number;
  precipitation?: number;
  [key: string]: unknown;
}

/**
 * Downsample a time-series dataset using the Largest-Triangle-Three-Buckets
 * algorithm (simplified). Keeps the visual shape while reducing points.
 */
function downsample(
  data: ChartDataPoint[],
  maxPoints: number,
): ChartDataPoint[] {
  if (data.length <= maxPoints) return data;

  const bucketSize = (data.length - 2) / (maxPoints - 2);
  const result: ChartDataPoint[] = [data[0]!]; // always keep first

  for (let i = 1; i < maxPoints - 1; i++) {
    const start = Math.floor((i - 1) * bucketSize) + 1;
    const end = Math.min(Math.floor(i * bucketSize) + 1, data.length);

    // Pick the point with the largest value across numeric fields
    let maxIdx = start;
    let maxVal = -Infinity;
    for (let j = start; j < end; j++) {
      const point = data[j];
      if (!point) continue;
      const val =
        (typeof point.temperature === "number" ? point.temperature : 0) +
        (typeof point.humidity === "number" ? point.humidity : 0) +
        (typeof point.precipitation === "number" ? point.precipitation : 0);
      if (val > maxVal) {
        maxVal = val;
        maxIdx = j;
      }
    }
    const selected = data[maxIdx];
    if (selected) result.push(selected);
  }

  result.push(data[data.length - 1]!); // always keep last
  return result;
}

/**
 * Compute a simple moving average for a numeric field.
 */
function movingAverage(
  data: ChartDataPoint[],
  field: string,
  window: number,
): ChartDataPoint[] {
  return data.map((point, idx) => {
    const start = Math.max(0, idx - window + 1);
    let sum = 0;
    let count = 0;
    for (let j = start; j <= idx; j++) {
      const v = data[j]?.[field];
      if (typeof v === "number") {
        sum += v;
        count++;
      }
    }
    return {
      ...point,
      [`${field}_ma`]: count > 0 ? sum / count : null,
    };
  });
}

const chartWorkerApi = {
  downsample,
  movingAverage,
};

export type ChartWorkerApi = typeof chartWorkerApi;

expose(chartWorkerApi);
