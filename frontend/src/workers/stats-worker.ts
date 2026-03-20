/**
 * Stats Aggregation Worker
 *
 * Offloads dashboard statistics computation: totals, percentages,
 * risk distribution, and trend calculations from the main thread.
 */

import { expose } from "comlink";

export interface AlertStat {
  id: number;
  risk_level: number;
  acknowledged: boolean;
  created_at: string;
}

export interface DashboardStats {
  total: number;
  critical: number;
  alert: number;
  safe: number;
  unacknowledged: number;
  criticalPercent: number;
  alertPercent: number;
  safePercent: number;
}

/**
 * Compute dashboard statistics from a raw alerts array.
 */
function computeStats(alerts: AlertStat[]): DashboardStats {
  const total = alerts.length;
  let critical = 0;
  let alert = 0;
  let safe = 0;
  let unacknowledged = 0;

  for (const a of alerts) {
    if (a.risk_level === 2) critical++;
    else if (a.risk_level === 1) alert++;
    else safe++;
    if (!a.acknowledged) unacknowledged++;
  }

  return {
    total,
    critical,
    alert,
    safe,
    unacknowledged,
    criticalPercent: total > 0 ? (critical / total) * 100 : 0,
    alertPercent: total > 0 ? (alert / total) * 100 : 0,
    safePercent: total > 0 ? (safe / total) * 100 : 0,
  };
}

/**
 * Group alerts by date (YYYY-MM-DD) and count per risk level.
 */
function groupByDate(
  alerts: AlertStat[],
): Array<{ date: string; critical: number; alert: number; safe: number }> {
  const map = new Map<
    string,
    { critical: number; alert: number; safe: number }
  >();

  for (const a of alerts) {
    const date = a.created_at.slice(0, 10); // YYYY-MM-DD
    const entry = map.get(date) ?? { critical: 0, alert: 0, safe: 0 };
    if (a.risk_level === 2) entry.critical++;
    else if (a.risk_level === 1) entry.alert++;
    else entry.safe++;
    map.set(date, entry);
  }

  return Array.from(map.entries())
    .map(([date, counts]) => ({ date, ...counts }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

const statsWorkerApi = {
  computeStats,
  groupByDate,
};

export type StatsWorkerApi = typeof statsWorkerApi;

expose(statsWorkerApi);
