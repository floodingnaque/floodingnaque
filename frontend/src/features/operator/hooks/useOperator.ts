/**
 * Operator Hooks
 *
 * TanStack Query hooks for the LGU operator dashboard.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type {
  CreateIncidentRequest,
  UpdateIncidentRequest,
} from "../services/operatorApi";
import { operatorApi } from "../services/operatorApi";

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const operatorKeys = {
  all: ["operator"] as const,
  incidents: () => [...operatorKeys.all, "incidents"] as const,
  incidentList: (params?: Record<string, unknown>) =>
    [...operatorKeys.incidents(), "list", params] as const,
  incidentStats: () => [...operatorKeys.incidents(), "stats"] as const,
  incidentAnalytics: () => [...operatorKeys.incidents(), "analytics"] as const,
  aars: () => [...operatorKeys.all, "aars"] as const,
  aarList: (params?: Record<string, unknown>) =>
    [...operatorKeys.aars(), "list", params] as const,
  broadcasts: () => [...operatorKeys.all, "broadcasts"] as const,
  broadcastList: (params?: Record<string, unknown>) =>
    [...operatorKeys.broadcasts(), "list", params] as const,
  residents: () => [...operatorKeys.all, "residents"] as const,
  residentList: (params?: Record<string, unknown>) =>
    [...operatorKeys.residents(), "list", params] as const,
};

// ─── Incidents ───────────────────────────────────────────────────────────────

export function useIncidents(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: operatorKeys.incidentList(params),
    queryFn: ({ signal }) => operatorApi.getIncidents(params, { signal }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useIncidentStats() {
  return useQuery({
    queryKey: operatorKeys.incidentStats(),
    queryFn: ({ signal }) => operatorApi.getIncidentStats({ signal }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useIncidentAnalytics() {
  return useQuery({
    queryKey: operatorKeys.incidentAnalytics(),
    queryFn: ({ signal }) => operatorApi.getIncidentAnalytics({ signal }),
    staleTime: 60_000,
    refetchInterval: 300_000,
  });
}

export function useCreateIncident() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateIncidentRequest) =>
      operatorApi.createIncident(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: operatorKeys.incidents() });
    },
    onError: () => toast.error("Failed to create incident"),
  });
}

export function useUpdateIncident() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateIncidentRequest }) =>
      operatorApi.updateIncident(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: operatorKeys.incidents() });
    },
    onError: () => toast.error("Failed to update incident"),
  });
}

export function useAdvanceIncident() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => operatorApi.advanceIncident(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: operatorKeys.incidents() });
    },
    onError: () => toast.error("Failed to advance incident"),
  });
}

// ─── After-Action Reports ────────────────────────────────────────────────────

export function useAARs(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: operatorKeys.aarList(params),
    queryFn: ({ signal }) => operatorApi.getAARs(params, { signal }),
    staleTime: 60_000,
  });
}

export function useCreateAAR() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      operatorApi.createAAR(data as never),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: operatorKeys.aars() });
    },
    onError: () => toast.error("Failed to create after-action report"),
  });
}

// ─── Broadcasts ──────────────────────────────────────────────────────────────

export function useBroadcasts(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: operatorKeys.broadcastList(params),
    queryFn: ({ signal }) => operatorApi.getBroadcasts(params, { signal }),
    staleTime: 30_000,
  });
}

export function useSendBroadcast() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      target_barangays: string[];
      channels: string[];
      message: string;
      priority: string;
      title?: string;
    }) => operatorApi.sendBroadcast(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: operatorKeys.broadcasts() });
    },
    onError: () => toast.error("Failed to send broadcast"),
  });
}

// ─── Residents ───────────────────────────────────────────────────────────────

export function useResidents(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: operatorKeys.residentList(params),
    queryFn: ({ signal }) => operatorApi.getResidents(params, { signal }),
    staleTime: 60_000,
    refetchInterval: 120_000,
  });
}
