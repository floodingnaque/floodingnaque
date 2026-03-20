/**
 * Compliance Health Hook
 *
 * Derives per-section compliance status from the system health endpoint.
 * Re-checks every 5 minutes via useSystemHealth's refetch mechanism.
 */

import { useMemo } from "react";

import { useSystemHealth } from "@/features/admin";
import type { SystemHealth } from "@/features/admin/services/adminApi";

export type ComplianceStatus = "compliant" | "partial" | "non-compliant";

export interface ComplianceCheck {
  section: string;
  status: ComplianceStatus;
  reason: string;
}

export interface EarlyWarningStatus {
  step: number;
  status: "active" | "degraded" | "inactive";
}

export interface ComplianceHealthResult {
  /** Overall system health data */
  health: SystemHealth | undefined;
  /** Per-RA-10121-section compliance checks */
  sectionChecks: Map<string, ComplianceCheck>;
  /** Per-early-warning-step live status */
  earlyWarningStatuses: Map<number, EarlyWarningStatus>;
  /** Overall score: compliant count / total */
  score: { compliant: number; total: number; percentage: number };
  /** Whether any section is non-compliant or partial */
  hasDegradation: boolean;
  /** ISO timestamp of last health check */
  lastChecked: string | null;
  /** Is the health query currently loading */
  isLoading: boolean;
  /** Is the health query in error state */
  isError: boolean;
  /** Refetch health data manually */
  refetch: () => void;
}

function deriveStatus(ok: boolean, partialOk?: boolean): ComplianceStatus {
  if (ok) return "compliant";
  if (partialOk) return "partial";
  return "non-compliant";
}

/**
 * Hook that evaluates compliance status from live system health.
 * Refetches every 5 minutes (300_000 ms).
 */
export function useComplianceHealth(): ComplianceHealthResult {
  const {
    data: health,
    isLoading,
    isError,
    refetch,
    dataUpdatedAt,
  } = useSystemHealth(true);

  const sectionChecks = useMemo(() => {
    const checks = new Map<string, ComplianceCheck>();

    if (!health) {
      // No data yet — everything unknown, treat as partial
      const sections = [
        "Sec. 2(a)",
        "Sec. 2(c)",
        "Sec. 2(f)",
        "Sec. 6(k)",
        "Sec. 6(l)",
        "Sec. 12",
        "Sec. 12(c)",
        "Sec. 14",
        "IRR Rule 8.2",
        "IRR Rule 10",
      ];
      for (const s of sections) {
        checks.set(s, {
          section: s,
          status: "partial",
          reason: "System health data unavailable",
        });
      }
      return checks;
    }

    const db = health.checks.database?.connected ?? false;
    const modelLoaded = health.checks.model_available ?? false;
    const schedulerRunning = health.checks.scheduler_running ?? false;
    const redis = health.checks.redis?.connected ?? false;
    const hasExternalApis = !!health.checks.external_apis;
    const modelVersion = health.model?.version;

    // Sec. 2(a) — 3-level risk classification requires model + DB
    checks.set("Sec. 2(a)", {
      section: "Sec. 2(a)",
      status: deriveStatus(modelLoaded && db, modelLoaded || db),
      reason:
        modelLoaded && db
          ? "Alert system active with 3-level risk classification"
          : !modelLoaded
            ? "ML model not loaded — risk classification unavailable"
            : "Database offline — cannot evaluate alerts",
    });

    // Sec. 2(c) — ML model trained on DRRMO records
    checks.set("Sec. 2(c)", {
      section: "Sec. 2(c)",
      status: deriveStatus(modelLoaded && !!modelVersion, modelLoaded),
      reason: modelLoaded
        ? `Model ${modelVersion || "unknown"} loaded with ${health.model?.features_count ?? "N/A"} features`
        : "ML model not available — training data integration inactive",
    });

    // Sec. 2(f) — Role-based dashboards require DB
    checks.set("Sec. 2(f)", {
      section: "Sec. 2(f)",
      status: deriveStatus(db, true),
      reason: db
        ? "Role-based dashboards (resident, operator, LGU) operational"
        : "Database offline — dashboards partially degraded",
    });

    // Sec. 6(k) — Real-time SSE alerts + SMS requires Redis + scheduler
    checks.set("Sec. 6(k)", {
      section: "Sec. 6(k)",
      status: deriveStatus(
        redis && schedulerRunning,
        redis || schedulerRunning,
      ),
      reason:
        redis && schedulerRunning
          ? "Real-time SSE alerts and SMS simulation active"
          : !redis
            ? "Redis offline — SSE delivery degraded"
            : "Scheduler stopped — alert evaluation paused",
    });

    // Sec. 6(l) — LGU workflow pipeline requires DB
    checks.set("Sec. 6(l)", {
      section: "Sec. 6(l)",
      status: deriveStatus(db),
      reason: db
        ? "LGU workflow pipeline (Alert → Resolution → AAR) operational"
        : "Database offline — workflow pipeline unavailable",
    });

    // Sec. 12 — Incident logging requires DB
    checks.set("Sec. 12", {
      section: "Sec. 12",
      status: deriveStatus(db),
      reason: db
        ? "Incident logging and MDRRMO officer tracking active"
        : "Database offline — incident logging unavailable",
    });

    // Sec. 12(c) — After-action reports require DB
    checks.set("Sec. 12(c)", {
      section: "Sec. 12(c)",
      status: deriveStatus(db),
      reason: db
        ? "After-action report module with NDRRMC/DILG submission tracking operational"
        : "Database offline — AAR module unavailable",
    });

    // Sec. 14 — Barangay-level risk mapping requires DB + model
    checks.set("Sec. 14", {
      section: "Sec. 14",
      status: deriveStatus(db && modelLoaded, db),
      reason:
        db && modelLoaded
          ? "Barangay-level risk mapping and incident tracking operational"
          : !db
            ? "Database offline — barangay data unavailable"
            : "Model not loaded — risk mapping degraded",
    });

    // IRR Rule 8.2 — GPS predictions + weather station integration
    checks.set("IRR Rule 8.2", {
      section: "IRR Rule 8.2",
      status: deriveStatus(modelLoaded && hasExternalApis, modelLoaded),
      reason:
        modelLoaded && hasExternalApis
          ? "GPS predictions and weather station integrations (PAGASA, OWM, Meteostat) active"
          : !modelLoaded
            ? "Model offline — prediction capability unavailable"
            : "External API status unknown",
    });

    // IRR Rule 10 — Post-disaster needs assessment requires DB
    checks.set("IRR Rule 10", {
      section: "IRR Rule 10",
      status: deriveStatus(db),
      reason: db
        ? "Impact tracking fields (affected/evacuated families, casualties) operational"
        : "Database offline — impact tracking unavailable",
    });

    return checks;
  }, [health]);

  const earlyWarningStatuses = useMemo(() => {
    const statuses = new Map<number, EarlyWarningStatus>();
    if (!health) {
      for (let i = 1; i <= 6; i++) {
        statuses.set(i, { step: i, status: "inactive" });
      }
      return statuses;
    }

    const db = health.checks.database?.connected ?? false;
    const model = health.checks.model_available ?? false;
    const scheduler = health.checks.scheduler_running ?? false;
    const redis = health.checks.redis?.connected ?? false;
    const apis = !!health.checks.external_apis;

    // Step 1: Detection & Monitoring — needs scheduler + external APIs
    const s1 = scheduler && apis;
    statuses.set(1, {
      step: 1,
      status: s1 ? "active" : scheduler || apis ? "degraded" : "inactive",
    });

    // Step 2: Risk Assessment — needs model
    statuses.set(2, { step: 2, status: model ? "active" : "inactive" });

    // Step 3: Warning Formulation — needs model + scheduler
    const s3 = model && scheduler;
    statuses.set(3, {
      step: 3,
      status: s3 ? "active" : model || scheduler ? "degraded" : "inactive",
    });

    // Step 4: Warning Dissemination — needs Redis + scheduler
    const s4 = redis && scheduler;
    statuses.set(4, {
      step: 4,
      status: s4 ? "active" : redis || scheduler ? "degraded" : "inactive",
    });

    // Step 5: Community Response — needs DB
    statuses.set(5, { step: 5, status: db ? "active" : "inactive" });

    // Step 6: Post-Event Review — needs DB
    statuses.set(6, { step: 6, status: db ? "active" : "inactive" });

    return statuses;
  }, [health]);

  const score = useMemo(() => {
    const total = sectionChecks.size;
    let compliant = 0;
    for (const check of sectionChecks.values()) {
      if (check.status === "compliant") compliant++;
    }
    return {
      compliant,
      total,
      percentage: total > 0 ? Math.round((compliant / total) * 100) : 0,
    };
  }, [sectionChecks]);

  const hasDegradation = useMemo(() => {
    for (const check of sectionChecks.values()) {
      if (check.status !== "compliant") return true;
    }
    return false;
  }, [sectionChecks]);

  const lastChecked = useMemo(() => {
    if (dataUpdatedAt) return new Date(dataUpdatedAt).toISOString();
    if (health?.timestamp) return health.timestamp;
    return null;
  }, [dataUpdatedAt, health]);

  return {
    health,
    sectionChecks,
    earlyWarningStatuses,
    score,
    hasDegradation,
    lastChecked,
    isLoading,
    isError,
    refetch: () => {
      refetch();
    },
  };
}
