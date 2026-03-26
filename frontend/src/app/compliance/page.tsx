/**
 * Compliance Page - RA 10121 & National DRRM Framework Alignment
 *
 * Displays how the Floodingnaque system aligns with:
 *   - Republic Act No. 10121 (Philippine DRRM Act of 2010)
 *   - Local DRRM protocols for Parañaque City
 *   - Barangay early warning procedures
 *
 * Compliance statuses are dynamically evaluated against live system health.
 */

import { formatDistanceToNow } from "date-fns";
import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  BookOpen,
  Building2,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileCheck,
  Globe,
  Landmark,
  Loader2,
  Megaphone,
  RefreshCw,
  Scale,
  ShieldCheck,
  Siren,
  Users,
  XCircle,
} from "lucide-react";
import { useRef } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { Badge } from "@/components/ui/badge";
import { GlassCard } from "@/components/ui/glass-card";
import { Separator } from "@/components/ui/separator";
import {
  useComplianceHealth,
  type ComplianceStatus,
} from "@/features/compliance";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// RA 10121 Compliance Matrix (static descriptions - status derived live)
// ---------------------------------------------------------------------------

interface ComplianceItem {
  section: string;
  requirement: string;
  implementation: string;
}

const RA_10121_MATRIX: ComplianceItem[] = [
  {
    section: "Sec. 2(a)",
    requirement:
      "Institutionalize policies relating to disaster risk reduction and management",
    implementation:
      "System implements 3-level risk classification (Safe/Alert/Critical) aligned with NDRRMC color-coded alert protocol.",
  },
  {
    section: "Sec. 2(c)",
    requirement:
      "Mainstream disaster risk reduction into development processes",
    implementation:
      "Machine learning model trained on 3,700+ official DRRMO flood records integrates historical disaster data into predictive system.",
  },
  {
    section: "Sec. 2(f)",
    requirement: "Develop and strengthen capacities of local communities",
    implementation:
      "Web-based prediction tool accessible to residents, operators, and LGU officials with role-based dashboards.",
  },
  {
    section: "Sec. 6(k)",
    requirement: "Establish early warning systems",
    implementation:
      "Real-time SSE alert delivery with SMS simulation, multi-channel broadcast (siren, SMS, social media, radio).",
  },
  {
    section: "Sec. 6(l)",
    requirement:
      "Coordinate and integrate activities of government departments",
    implementation:
      "LGU workflow pipeline: Alert → Confirmation → Broadcast → Resolution → After-Action Report.",
  },
  {
    section: "Sec. 12",
    requirement: "Local DRRM Office functions and responsibilities",
    implementation:
      "Incident logging system with MDRRMO officer tracking, barangay-level reporting, and decision support engine.",
  },
  {
    section: "Sec. 12(c)",
    requirement: "Prepare and submit reports on disaster situations",
    implementation:
      "After-action reporting module with NDRRMC/DILG submission tracking and RA 10121 compliance flags.",
  },
  {
    section: "Sec. 14",
    requirement: "Barangay DRRM Committee responsibilities",
    implementation:
      "Barangay-level risk mapping, per-barangay incident tracking, and localized early warning procedures.",
  },
  {
    section: "IRR Rule 8.2",
    requirement: "Community-based monitoring and early warning",
    implementation:
      "GPS-based location predictions, weather station integration (PAGASA, OWM, Meteostat), and automated alert escalation.",
  },
  {
    section: "IRR Rule 10",
    requirement: "Post-disaster needs assessment",
    implementation:
      "Incident impact tracking (affected/evacuated families, casualties, damage estimates) and after-action review process.",
  },
];

const STATUS_BADGE_MAP: Record<
  ComplianceStatus,
  { label: string; className: string; Icon: React.ElementType }
> = {
  compliant: {
    label: "Compliant",
    className: "border-risk-safe/30 bg-risk-safe/10 text-risk-safe",
    Icon: CheckCircle2,
  },
  partial: {
    label: "Partial",
    className: "border-risk-alert/30 bg-risk-alert/10 text-risk-alert",
    Icon: AlertTriangle,
  },
  "non-compliant": {
    label: "Non-Compliant",
    className: "border-red-500/30 bg-red-500/10 text-red-500",
    Icon: XCircle,
  },
};

// ---------------------------------------------------------------------------
// Local DRRM Protocols
// ---------------------------------------------------------------------------

interface Protocol {
  icon: React.ElementType;
  title: string;
  body: string;
  healthKey: string;
}

const LOCAL_PROTOCOLS: Protocol[] = [
  {
    icon: Siren,
    title: "Alert Level Classification",
    healthKey: "Sec. 2(a)",
    body: "Three-tier system matching NDRRMC color codes: Green (Safe), Yellow/Orange (Alert), Red (Critical). Thresholds calibrated per Parañaque City flood history.",
  },
  {
    icon: Users,
    title: "MDRRMO Coordination",
    healthKey: "Sec. 2(f)",
    body: "Operator-tier dashboard provides real-time flood status, decision support engine, tidal risk indicators, and barangay risk maps for MDRRMO staff.",
  },
  {
    icon: Megaphone,
    title: "Multi-Channel Broadcast",
    healthKey: "Sec. 6(k)",
    body: "Alert dissemination via SMS, siren activation, social media, radio, megaphone - all tracked with delivery status and timestamp logging.",
  },
  {
    icon: Building2,
    title: "Evacuation Support",
    healthKey: "IRR Rule 10",
    body: "Incident tracking includes affected families, evacuated families, and casualty counts. Barangay-level granularity for targeted response.",
  },
];

// ---------------------------------------------------------------------------
// Barangay Early Warning Procedures
// ---------------------------------------------------------------------------

interface EWStep {
  step: number;
  title: string;
  description: string;
  systemRole: string;
}

const EARLY_WARNING_STEPS: EWStep[] = [
  {
    step: 1,
    title: "Detection & Monitoring",
    description:
      "Continuous weather monitoring from PAGASA, OpenWeatherMap, and Meteostat stations.",
    systemRole:
      "Automated data ingestion with fallback chain and circuit breakers.",
  },
  {
    step: 2,
    title: "Risk Assessment",
    description:
      "AI model evaluates flood probability using 10+ features (precipitation, humidity, interactions).",
    systemRole:
      "Random Forest classifier with 3-level risk output and confidence scoring.",
  },
  {
    step: 3,
    title: "Warning Formulation",
    description:
      "Risk classification generates structured alert with contributing factors and XAI explanation.",
    systemRole:
      "Smart Alert Evaluator with escalation state machine and false-alarm suppression.",
  },
  {
    step: 4,
    title: "Warning Dissemination",
    description:
      "Multi-channel broadcast to affected barangays through official communication channels.",
    systemRole:
      "SMS simulation panel, SSE real-time push, delivery tracking per channel.",
  },
  {
    step: 5,
    title: "Community Response",
    description:
      "Barangay DRRM committees activate evacuation procedures and secure infrastructure.",
    systemRole:
      "LGU workflow pipeline tracks confirmation, broadcast, and resolution states.",
  },
  {
    step: 6,
    title: "Post-Event Review",
    description:
      "After-action report filed documenting timeline, response effectiveness, and lessons learned.",
    systemRole:
      "AAR module with NDRRMC/DILG submission tracking and compliance scoring.",
  },
];

// ---------------------------------------------------------------------------
// References
// ---------------------------------------------------------------------------

interface Reference {
  icon: React.ElementType;
  title: string;
  subtitle: string;
  detail: string;
  url: string;
  lastVerified: string;
}

const REFERENCES: Reference[] = [
  {
    icon: Landmark,
    title: "Republic Act No. 10121",
    subtitle: "Philippine DRRM Act of 2010",
    detail:
      "Strengthening the Philippine disaster risk reduction and management system.",
    url: "https://www.officialgazette.gov.ph/2010/05/27/republic-act-no-10121/",
    lastVerified: "2025-12-15",
  },
  {
    icon: BookOpen,
    title: "IRR of RA 10121",
    subtitle: "Implementing Rules & Regulations",
    detail:
      "Detailed provisions for national, regional, and local DRRM functions.",
    url: "https://ndrrmc.gov.ph/attachments/article/95/Implementing_Rules_and_Regulations_RA_10121.pdf",
    lastVerified: "2025-12-15",
  },
  {
    icon: ShieldCheck,
    title: "NDRRMC Memoranda",
    subtitle: "National Council Issuances",
    detail:
      "Color-coded alert protocols, reporting templates, and coordination procedures.",
    url: "https://ndrrmc.gov.ph/",
    lastVerified: "2025-12-15",
  },
];

// ---------------------------------------------------------------------------
// EW Status helpers
// ---------------------------------------------------------------------------

const EW_STATUS_STYLES: Record<
  string,
  { dot: string; label: string; ring: string }
> = {
  active: {
    dot: "bg-risk-safe",
    label: "Active",
    ring: "ring-risk-safe/30",
  },
  degraded: {
    dot: "bg-risk-alert",
    label: "Degraded",
    ring: "ring-risk-alert/30",
  },
  inactive: {
    dot: "bg-red-500",
    label: "Inactive",
    ring: "ring-red-500/30",
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CompliancePage() {
  const ref1 = useRef<HTMLDivElement>(null);
  const ref2 = useRef<HTMLDivElement>(null);
  const ref3 = useRef<HTMLDivElement>(null);
  const in1 = useInView(ref1, { once: true, amount: 0.1 });
  const in2 = useInView(ref2, { once: true, amount: 0.1 });
  const in3 = useInView(ref3, { once: true, amount: 0.1 });

  const {
    sectionChecks,
    earlyWarningStatuses,
    score,
    hasDegradation,
    lastChecked,
    isLoading,
    refetch,
  } = useComplianceHealth();

  const lastCheckedLabel = lastChecked
    ? formatDistanceToNow(new Date(lastChecked), { addSuffix: true })
    : "checking…";

  // Dynamic header badge
  const headerBadgeClass = hasDegradation
    ? "border-risk-alert/30 bg-risk-alert/10 text-risk-alert"
    : "border-risk-safe/30 bg-risk-safe/10 text-risk-safe";
  const headerBadgeLabel = hasDegradation
    ? "Partial Compliance"
    : "RA 10121 Aligned";

  return (
    <div className="space-y-0">
      {/* ── Header ── */}
      <div className="w-full px-6 pt-6 pb-2">
        <PageHeader
          icon={Scale}
          title="National Framework Compliance"
          subtitle="Alignment with RA 10121, local DRRM protocols, and barangay early warning procedures"
          badge={
            <Badge
              variant="outline"
              className={cn("text-xs", headerBadgeClass)}
            >
              {headerBadgeLabel}
            </Badge>
          }
        />
      </div>

      {/* ═══ Overall Score Banner ═══ */}
      <div className="w-full px-6">
        <GlassCard intensity="medium" className="relative overflow-hidden">
          <div
            className={cn(
              "absolute inset-x-0 top-0 h-1",
              hasDegradation
                ? "bg-linear-to-r from-risk-alert/60 to-risk-alert/20"
                : "bg-linear-to-r from-risk-safe/60 to-risk-safe/20",
            )}
          />
          <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              {/* Score circle */}
              <div
                className={cn(
                  "h-14 w-14 rounded-full flex items-center justify-center text-lg font-bold ring-2",
                  hasDegradation
                    ? "bg-risk-alert/10 text-risk-alert ring-risk-alert/30"
                    : "bg-risk-safe/10 text-risk-safe ring-risk-safe/30",
                )}
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  `${score.percentage}%`
                )}
              </div>
              <div>
                <p className="text-sm font-semibold">
                  {score.compliant} of {score.total} sections compliant
                  {!isLoading && (
                    <span className="ml-1 text-muted-foreground font-normal">
                      - {score.percentage}%
                    </span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">
                  Overall RA 10121 compliance score based on live system health
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" />
                <span>Last checked {lastCheckedLabel}</span>
              </div>
              <button
                onClick={() => refetch()}
                className="flex items-center gap-1 rounded-md px-2 py-1 hover:bg-muted transition-colors"
                title="Refresh compliance checks"
              >
                <RefreshCw
                  className={cn("h-3.5 w-3.5", isLoading && "animate-spin")}
                />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          {/* Degradation warning banner */}
          {hasDegradation && !isLoading && (
            <div className="border-t border-risk-alert/20 bg-risk-alert/5 px-4 sm:px-5 py-3 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-risk-alert shrink-0" />
              <p className="text-xs text-risk-alert">
                One or more compliance-linked features are degraded or offline.
                Review the sections below for details.
              </p>
            </div>
          )}
        </GlassCard>
      </div>

      {/* ═══ Section 1: RA 10121 Compliance Matrix ═══ */}
      <section ref={ref1} className="bg-muted/30 py-12 w-full px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={in1 ? "show" : "hidden"}
        >
          <SectionHeading
            label="Republic Act No. 10121"
            title="Philippine DRRM Act Compliance"
            subtitle="Systematic mapping of system features to statutory requirements of the Philippine Disaster Risk Reduction and Management Act of 2010."
          />

          <div className="space-y-4">
            {RA_10121_MATRIX.map((item, i) => {
              const check = sectionChecks.get(item.section);
              const liveStatus: ComplianceStatus = check?.status ?? "partial";
              const badge = STATUS_BADGE_MAP[liveStatus];
              const BadgeIcon = badge.Icon;

              return (
                <motion.div key={i} variants={fadeUp}>
                  <GlassCard
                    intensity="medium"
                    className="relative overflow-hidden"
                  >
                    <div className="absolute inset-x-0 top-0 h-1 bg-linear-to-r from-primary/60 to-primary/20" />
                    <div className="p-5 sm:p-6">
                      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                        {/* Section badge */}
                        <div className="shrink-0 flex items-center gap-2">
                          <div className="h-10 w-10 rounded-xl bg-linear-to-br from-primary/20 to-primary/10 ring-1 ring-primary/30 flex items-center justify-center">
                            <FileCheck className="h-5 w-5 text-primary" />
                          </div>
                          <Badge
                            variant="outline"
                            className="font-mono text-xs border-primary/30 bg-primary/10 text-primary"
                          >
                            {item.section}
                          </Badge>
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0 space-y-2">
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-sm font-medium leading-snug">
                              {item.requirement}
                            </p>
                            <Badge
                              variant="outline"
                              className={cn(
                                "shrink-0 text-xs",
                                badge.className,
                              )}
                            >
                              <BadgeIcon className="mr-1 h-3 w-3" />
                              {badge.label}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed">
                            {item.implementation}
                          </p>
                          {/* Live status reason */}
                          {check && (
                            <p
                              className={cn(
                                "text-xs leading-relaxed italic",
                                liveStatus === "compliant"
                                  ? "text-risk-safe/80"
                                  : liveStatus === "partial"
                                    ? "text-risk-alert/80"
                                    : "text-red-500/80",
                              )}
                            >
                              {check.reason}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  </GlassCard>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </section>

      {/* ═══ Section 2: Local DRRM Protocols ═══ */}
      <section ref={ref2} className="bg-background py-12 w-full px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={in2 ? "show" : "hidden"}
        >
          <SectionHeading
            label="Parañaque City DRRM"
            title="Local Protocol Alignment"
            subtitle="How the system supports the Parañaque City Disaster Risk Reduction and Management Office procedures."
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {LOCAL_PROTOCOLS.map((p, i) => {
              const check = sectionChecks.get(p.healthKey);
              const liveStatus: ComplianceStatus = check?.status ?? "partial";
              const statusBadge = STATUS_BADGE_MAP[liveStatus];
              const StatusIcon = statusBadge.Icon;

              return (
                <motion.div key={i} variants={fadeUp}>
                  <GlassCard
                    intensity="medium"
                    className="relative overflow-hidden h-full"
                  >
                    <div className="absolute inset-x-0 top-0 h-1 bg-linear-to-r from-primary/60 to-primary/20" />
                    <div className="p-6 space-y-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-xl bg-linear-to-br from-primary/20 to-primary/10 ring-1 ring-primary/30 flex items-center justify-center">
                            <p.icon className="h-5 w-5 text-primary" />
                          </div>
                          <h3 className="font-semibold tracking-tight">
                            {p.title}
                          </h3>
                        </div>
                        <Badge
                          variant="outline"
                          className={cn(
                            "shrink-0 text-xs",
                            statusBadge.className,
                          )}
                        >
                          <StatusIcon className="mr-1 h-3 w-3" />
                          {statusBadge.label}
                        </Badge>
                      </div>
                      <Separator className="opacity-30" />
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {p.body}
                      </p>
                    </div>
                  </GlassCard>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </section>

      {/* ═══ Section 3: Barangay Early Warning Procedures ═══ */}
      <section ref={ref3} className="bg-muted/30 py-12 w-full px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={in3 ? "show" : "hidden"}
        >
          <SectionHeading
            label="Early Warning System"
            title="Barangay Early Warning Procedures"
            subtitle="End-to-end warning lifecycle from detection through community response and post-event review."
          />

          <div className="relative">
            {/* Vertical timeline line */}
            <div className="absolute left-6 top-0 bottom-0 w-px bg-linear-to-b from-primary/40 via-primary/20 to-transparent hidden sm:block" />

            <div className="space-y-6">
              {EARLY_WARNING_STEPS.map((step, i) => {
                const ewStatus = earlyWarningStatuses.get(step.step);
                const statusKey = ewStatus?.status ?? "inactive";
                const ewStyle = EW_STATUS_STYLES[statusKey]!;

                return (
                  <motion.div key={i} variants={fadeUp} className="relative">
                    <GlassCard
                      intensity="medium"
                      className="relative overflow-hidden sm:ml-14"
                    >
                      <div className="absolute inset-x-0 top-0 h-1 bg-linear-to-r from-primary/60 to-primary/20" />

                      {/* Step number circle (desktop) */}
                      <div className="absolute -left-14 top-6 hidden sm:flex h-9 w-9 items-center justify-center rounded-full bg-primary text-white font-bold text-sm ring-4 ring-background">
                        {step.step}
                      </div>

                      <div className="p-5 sm:p-6 space-y-3">
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-3">
                            {/* Step number (mobile) */}
                            <div className="sm:hidden h-8 w-8 rounded-full bg-primary text-white font-bold text-sm flex items-center justify-center shrink-0">
                              {step.step}
                            </div>
                            <h3 className="font-semibold tracking-tight">
                              {step.title}
                            </h3>
                          </div>
                          {/* Live status indicator */}
                          <div
                            className={cn(
                              "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs ring-1",
                              ewStyle.ring,
                            )}
                          >
                            <span
                              className={cn(
                                "h-2 w-2 rounded-full",
                                ewStyle.dot,
                                statusKey === "active" && "animate-pulse",
                              )}
                            />
                            <span className="text-muted-foreground">
                              {ewStyle.label}
                            </span>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {step.description}
                        </p>
                        <div className="flex items-start gap-2 rounded-lg bg-primary/5 border border-primary/10 px-3 py-2">
                          <Globe className="h-4 w-4 shrink-0 text-primary mt-0.5" />
                          <p className="text-xs text-muted-foreground leading-relaxed">
                            <span className="font-medium text-foreground">
                              System Role:{" "}
                            </span>
                            {step.systemRole}
                          </p>
                        </div>
                      </div>
                    </GlassCard>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </motion.div>
      </section>

      {/* ═══ Section 4: Key References ═══ */}
      <section className="bg-background py-12 w-full px-6">
        <div>
          <SectionHeading
            label="References"
            title="Legal & Regulatory Framework"
            subtitle="Primary legislation and guidelines governing disaster risk reduction in the Philippines."
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {REFERENCES.map((ref, i) => (
              <a
                key={i}
                href={ref.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block group"
              >
                <GlassCard
                  intensity="light"
                  className="relative overflow-hidden h-full transition-all group-hover:ring-1 group-hover:ring-primary/30"
                >
                  <div className="absolute inset-x-0 top-0 h-1 bg-linear-to-r from-primary/40 to-primary/10" />
                  <div className="p-5 space-y-2">
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 rounded-lg bg-linear-to-br from-primary/15 to-primary/5 ring-1 ring-primary/20 flex items-center justify-center">
                        <ref.icon className="h-4 w-4 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <p className="text-sm font-semibold truncate">
                            {ref.title}
                          </p>
                          <ExternalLink className="h-3 w-3 text-muted-foreground shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {ref.subtitle}
                        </p>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {ref.detail}
                    </p>
                    <p className="text-[10px] text-muted-foreground/60">
                      Last verified: {ref.lastVerified}
                    </p>
                  </div>
                </GlassCard>
              </a>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
