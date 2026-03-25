/**
 * Resident TanStack Query Hooks
 *
 * Cached, auto-refetching hooks for resident-specific data:
 * household profile, personal report history, evacuation, and alerts.
 */

import { communityApi } from "@/features/community/services/communityApi";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";

import {
  residentApi,
  type HouseholdProfile,
  type HouseholdProfileUpdate,
  type MyReportsResponse,
} from "../services/residentApi";

// ---------------------------------------------------------------------------
// Query Key Factory
// ---------------------------------------------------------------------------

export const residentKeys = {
  all: ["resident"] as const,
  household: () => [...residentKeys.all, "household"] as const,
  myReports: (params?: { limit?: number; page?: number }) =>
    [...residentKeys.all, "my-reports", params] as const,
  communityReports: (params?: Record<string, unknown>) =>
    [...residentKeys.all, "community-reports", params] as const,
};

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/** Fetch the current user's household/resident profile */
export function useHouseholdProfile(
  options?: Omit<UseQueryOptions<HouseholdProfile>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: residentKeys.household(),
    queryFn: ({ signal }) => residentApi.getHouseholdProfile({ signal }),
    staleTime: 5 * 60_000,
    ...options,
  });
}

/** Fetch the resident's own community reports */
export function useMyReports(params?: { limit?: number; page?: number }) {
  return useQuery<MyReportsResponse>({
    queryKey: residentKeys.myReports(params),
    queryFn: ({ signal }) => residentApi.getMyReports(params, { signal }),
    staleTime: 30_000,
  });
}

/** Fetch verified community reports (visible to all residents) */
export function useCommunityReports(params?: {
  barangay?: string;
  hours?: number;
  limit?: number;
  page?: number;
}) {
  return useQuery({
    queryKey: residentKeys.communityReports(params),
    queryFn: () => communityApi.getReports({ ...params, verified: true }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/** Update household profile */
export function useUpdateHouseholdProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: HouseholdProfileUpdate) =>
      residentApi.updateHouseholdProfile(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: residentKeys.household() });
      toast.success("Profile updated successfully");
    },
    onError: () => {
      toast.error("Failed to update profile");
    },
  });
}

/** Submit a new community flood report */
export function useSubmitReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => communityApi.submitReport(formData),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: residentKeys.myReports() });
      qc.invalidateQueries({ queryKey: residentKeys.communityReports() });
      toast.success("Report submitted successfully!");
    },
    onError: () => {
      toast.error("Failed to submit report");
    },
  });
}
