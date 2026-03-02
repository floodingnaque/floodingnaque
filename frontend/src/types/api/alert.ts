import type { RiskLevel } from './prediction';
import type { PaginationParams, DateRangeParams } from './common';

export interface Alert {
  id: number;
  risk_level: RiskLevel;
  message: string;
  location?: string;
  latitude?: number;
  longitude?: number;
  triggered_at: string;
  expires_at?: string;
  acknowledged: boolean;
  created_at: string;
  updated_at?: string;
  // Smart alert fields
  confidence_score?: number;
  rainfall_3h?: number;
  escalation_state?: 'initial' | 'escalated' | 'auto_escalated' | 'suppressed';
  escalation_reason?: string;
  contributing_factors?: string[];
}

export type AlertDeliveryStatus = 'pending' | 'delivered' | 'failed';

export interface AlertParams extends PaginationParams, DateRangeParams {
  risk_level?: RiskLevel;
  acknowledged?: boolean;
}

export interface AlertHistory {
  alerts: Alert[];
  summary: {
    total: number;
    by_risk_level: Record<RiskLevel, number>;
    acknowledged: number;
    pending: number;
  };
}

export interface SSEAlertEvent {
  type: 'alert' | 'heartbeat' | 'connection';
  data: SSEAlertData | SSEHeartbeatData | SSEConnectionData;
}

export interface SSEAlertData {
  alert: Alert;
  timestamp: string;
}

export interface SSEHeartbeatData {
  timestamp: string;
  connections: number;
}

export interface SSEConnectionData {
  status: 'connected' | 'disconnected';
  client_id: string;
}
