/**
 * Dashboard Feature Types
 *
 * Shared TypeScript interfaces for the enhanced dashboard panels.
 */

export interface RiverReading {
  station_id: string;
  station_name?: string;
  water_level: number;
  alarm_level: number;
  critical_level: number;
  timestamp: string;
}

export interface RiverStation {
  station_id: string;
  station_name: string;
  readings: RiverReading[];
  latest: RiverReading | null;
}

export interface RainfallPoint {
  time: string;
  mm: number;
  intensity: "light" | "moderate" | "heavy";
}

export interface RainfallMetrics {
  current: number;
  rolling3h: number;
  trend: "rising" | "falling" | "steady";
  intensity: "light" | "moderate" | "heavy";
}

export interface FeatureContribution {
  name: string;
  label: string;
  percentage: number;
}

// ---------------------------------------------------------------------------
// Analytics Panel Types
// ---------------------------------------------------------------------------

/** Flood frequency per barangay for horizontal bar chart */
export interface FloodFrequencyItem {
  barangay: string;
  events: number;
}

/** Year-over-year flood trend data */
export interface YearlyFloodTrend {
  year: string;
  events: number;
  rain: number;
}

/** Monthly rainfall vs flood events for seasonal chart */
export interface MonthlyFloodTrend {
  month: string;
  rain: number;
  events: number;
}

/** Individual historical flood event for the events table */
export interface FloodEvent {
  id: number;
  date: string;
  barangay: string;
  depth: string;
  disturbance: string;
  duration: string;
}

/** Rainfall-flood scatter data point */
export interface RainfallFloodPoint {
  rain: number;
  flood: number;
}

/** Seasonal risk for radar chart */
export interface SeasonalRisk {
  season: string;
  risk: number;
}

/** ML model confidence metrics */
export interface ModelMetrics {
  overall: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  cv_mean: number;
  cv_std: number;
  ensemble_agreement: number;
  calibration: number;
}

/** Single calibration curve data point */
export interface CalibrationPoint {
  prob: number;
  actual: number;
}

/** Summary stats for historical flood data */
export interface FloodHistorySummary {
  totalEvents: number;
  barangaysHit: string;
  worstMonth: string;
  mostAffected: string;
}

/** Aggregated response from analytics API */
export interface FloodHistoryData {
  available?: boolean;
  frequency: FloodFrequencyItem[];
  yearly: YearlyFloodTrend[];
  monthly: MonthlyFloodTrend[];
  recentEvents: FloodEvent[];
  summary: FloodHistorySummary;
}

/** Model metrics response from the API */
export interface ModelMetricsData {
  available?: boolean;
  metrics: ModelMetrics;
  cvFolds: number[];
  calibration: CalibrationPoint[];
  modelVersion: string;
  modelName: string;
}

// ---------------------------------------------------------------------------
// Emergency Command Panel Types
// ---------------------------------------------------------------------------

/** Barangay operational status for the emergency command board */
export interface BarangayStatus {
  name: string;
  risk: "Critical" | "Alert" | "Safe";
  alerts: number;
  evac_open: boolean;
  evac_cap: number;
  evac_occ: number;
  responders: number;
  road: "Impassable" | "Passable (light)" | "Passable (all)";
}

/** A single event in the incident timeline */
export interface IncidentTimelineEntry {
  time: string;
  event: string;
  level: "info" | "Alert" | "Critical";
}

// ---------------------------------------------------------------------------
// Flood Risk Heatmap Types
// ---------------------------------------------------------------------------

/** A single cell in the flood risk heatmap grid */
export interface HeatmapCell {
  name: string;
  risk: number;
  freq: number;
  trend: number;
}

// ---------------------------------------------------------------------------
// Alert Channel Panel Types
// ---------------------------------------------------------------------------

/** SMS delivery log entry */
export interface SmsLogEntry {
  time: string;
  recipients: number;
  barangays: string[];
  status: string;
  type: "Critical" | "Alert" | "Info";
  rate: number;
}

import type { LucideIcon } from "lucide-react";

/** Communication channel descriptor */
export interface AlertChannel {
  name: string;
  icon: LucideIcon;
  status: "Primary" | "Fallback" | "Active" | "Planned";
  coverage: string;
  cost: string;
  latency: string;
}

/** SMS message template for a risk level */
export interface SmsTemplate {
  level: string;
  title: string;
  color: string;
  msg: string;
}

// ---------------------------------------------------------------------------
// Flood Preparedness Guide Types
// ---------------------------------------------------------------------------

/** A single guide item (accordion entry) */
export interface PreparednessItem {
  icon: LucideIcon;
  title: string;
  desc: string;
}

/** A preparedness phase (before / during / after) */
export interface PreparednessPhase {
  icon: LucideIcon;
  label: string;
  color: string;
  items: PreparednessItem[];
}

/** Emergency contact for the preparedness panel */
export interface EmergencyContact {
  name: string;
  number: string;
  icon: string;
}
