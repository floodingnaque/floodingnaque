/**
 * LGU Workflow Types
 *
 * Types for the RA 10121-compliant LGU incident management pipeline:
 *   Alert → LGU Confirmation → Public Broadcast → Resolution → AAR
 */

import type { RiskLevel } from "./prediction";

// ---------------------------------------------------------------------------
// Incident
// ---------------------------------------------------------------------------

export type IncidentStatus =
  | "alert_raised"
  | "lgu_confirmed"
  | "broadcast_sent"
  | "resolved"
  | "closed";

export type IncidentType =
  | "flood"
  | "storm_surge"
  | "landslide"
  | "flash_flood";

export type IncidentSource =
  | "manual"
  | "system_alert"
  | "barangay_report"
  | "pagasa";

export interface Incident {
  id: number;
  title: string;
  description: string | null;
  incident_type: IncidentType;
  risk_level: RiskLevel;
  barangay: string;
  location_detail: string | null;
  latitude: number | null;
  longitude: number | null;
  status: IncidentStatus;
  confirmed_by: string | null;
  confirmed_at: string | null;
  broadcast_sent_at: string | null;
  broadcast_channels: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  affected_families: number;
  evacuated_families: number;
  casualties: number;
  estimated_damage: number | null;
  source: IncidentSource;
  related_alert_id: number | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface IncidentStats {
  total_active: number;
  by_status: Record<IncidentStatus, number>;
  by_risk_level: Record<string, number>;
}

// ---------------------------------------------------------------------------
// After-Action Report
// ---------------------------------------------------------------------------

export type AARStatus = "draft" | "submitted" | "reviewed" | "approved";

export interface AfterActionReport {
  id: number;
  incident_id: number;
  title: string;
  summary: string;
  timeline: string | null;
  response_actions: string | null;
  resources_deployed: string | null;
  response_time_minutes: number | null;
  evacuation_time_minutes: number | null;
  warning_lead_time_minutes: number | null;
  prediction_accuracy: number | null;
  lessons_learned: string | null;
  recommendations: string | null;
  follow_up_actions: string | null;
  ra10121_compliant: boolean;
  submitted_to_ndrrmc: boolean;
  submitted_to_dilg: boolean;
  prepared_by: string | null;
  reviewed_by: string | null;
  approved_by: string | null;
  status: AARStatus;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Workflow Analytics
// ---------------------------------------------------------------------------

export interface WorkflowAnalytics {
  avg_confirm_minutes: number | null;
  avg_broadcast_minutes: number | null;
  avg_resolve_minutes: number | null;
  total_incidents: number;
  resolved_incidents: number;
  closed_incidents: number;
  false_alarm_rate: number;
  false_alarm_count: number;
  total_aars: number;
  approved_aars: number;
  compliant_aars: number;
  aar_completion_rate: number;
  monthly_frequency: { year: number; month: number; count: number }[];
  stalled_incidents: number;
}

// ---------------------------------------------------------------------------
// LGU Workflow Pipeline Steps
// ---------------------------------------------------------------------------

export interface WorkflowStep {
  status: IncidentStatus;
  label: string;
  description: string;
}

export const LGU_WORKFLOW_STEPS: WorkflowStep[] = [
  {
    status: "alert_raised",
    label: "Alert Raised",
    description: "System or manual flood alert generated",
  },
  {
    status: "lgu_confirmed",
    label: "LGU Confirmed",
    description: "MDRRMO/LGU officer confirms the alert",
  },
  {
    status: "broadcast_sent",
    label: "Public Broadcast",
    description: "Warning broadcast to affected residents",
  },
  {
    status: "resolved",
    label: "Resolved",
    description: "Incident resolved, area declared safe",
  },
  {
    status: "closed",
    label: "Closed",
    description: "After-action report filed, incident archived",
  },
];
