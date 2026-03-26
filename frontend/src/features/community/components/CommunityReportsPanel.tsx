/**
 * CommunityReportsPanel
 *
 * Inline incident report form + recent community reports list.
 * Merges the design of the original IncidentPanel with existing
 * community feature hooks (useSubmitReport, useCommunityReports).
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BARANGAYS } from "@/config/paranaque";
import {
  useCommunityReports,
  useSubmitReport,
} from "@/features/community/hooks/useCommunityReports";
import { cn } from "@/lib/utils";
import type { CommunityReport } from "@/types";
import {
  Camera,
  CheckCircle2,
  ClipboardList,
  Construction,
  FileText,
  CarFront,
  TrendingUp,
  Upload,
  Waves,
} from "lucide-react";
import { memo, useCallback, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const INCIDENT_TYPES = [
  {
    value: "flooding",
    label: "Flooding",
    icon: <Waves className="h-3.5 w-3.5 inline" />,
    color: "text-blue-400 border-blue-400/40 bg-blue-400/10",
  },
  {
    value: "blocked_drainage",
    label: "Blocked Drainage",
    icon: <Construction className="h-3.5 w-3.5 inline" />,
    color: "text-risk-alert border-risk-alert/40 bg-risk-alert/10",
  },
  {
    value: "rising_water",
    label: "Rising Water",
    icon: <TrendingUp className="h-3.5 w-3.5 inline" />,
    color: "text-cyan-400 border-cyan-400/40 bg-cyan-400/10",
  },
  {
    value: "road_closure",
    label: "Road Impassable",
    icon: <CarFront className="h-3.5 w-3.5 inline" />,
    color: "text-risk-critical border-risk-critical/40 bg-risk-critical/10",
  },
  {
    value: "other",
    label: "Other",
    icon: <FileText className="h-3.5 w-3.5 inline" />,
    color: "text-muted-foreground border-border bg-muted",
  },
] as const;

const MAX_DESC = 300;
const MAX_PHOTO_SIZE = 5 * 1024 * 1024; // 5 MB
const ACCEPTED_IMAGE_TYPES = "image/jpeg,image/png,image/webp";

const BARANGAY_NAMES = BARANGAYS.map((b) => b.name).sort();

// ---------------------------------------------------------------------------
// Report row component
// ---------------------------------------------------------------------------

function ReportRow({ report }: { report: CommunityReport }) {
  const typeIcon =
    report.risk_label === "Critical"
      ? <Waves className="h-4 w-4" />
      : report.risk_label === "Alert"
        ? <Construction className="h-4 w-4" />
        : <TrendingUp className="h-4 w-4" />;

  const credibility = report.credibility_score ?? 0;

  return (
    <div className="flex items-center justify-between py-2 border-b border-border last:border-b-0">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-base shrink-0">{typeIcon}</span>
        <div className="min-w-0">
          <div className="text-[11px] text-foreground font-mono truncate">
            {report.description ?? report.risk_label}
          </div>
          <div className="text-[9px] text-muted-foreground font-mono">
            {report.barangay ?? "Unknown"} ·{" "}
            {new Date(report.created_at).toLocaleTimeString("en-PH", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        {report.photo_url && (
          <Badge variant="outline" className="text-[9px] px-1.5 py-0 gap-0.5">
            <Camera className="h-2.5 w-2.5" />
            Photo
          </Badge>
        )}
        <Badge
          variant="outline"
          className={cn(
            "text-[9px] px-1.5 py-0",
            report.status === "accepted"
              ? "text-risk-safe border-risk-safe/40 bg-risk-safe/10"
              : "text-risk-alert border-risk-alert/40 bg-risk-alert/10",
          )}
        >
          {report.status === "accepted" ? "Verified" : "Pending"}
        </Badge>
        <span
          className={cn(
            "text-[10px] font-mono",
            credibility >= 0.8
              ? "text-risk-safe"
              : credibility >= 0.6
                ? "text-risk-alert"
                : "text-risk-critical",
          )}
        >
          {Math.round(credibility * 100)}%
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const CommunityReportsPanel = memo(function CommunityReportsPanel() {
  const [step, setStep] = useState<"form" | "submitted">("form");
  const [incidentType, setIncidentType] = useState("");
  const [barangay, setBarangay] = useState("");
  const [desc, setDesc] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const [referenceId] = useState(
    () => `RPT-${crypto.randomUUID().slice(0, 6).toUpperCase()}`,
  );

  const { data: reportsData, isLoading: reportsLoading } = useCommunityReports({
    limit: 5,
  });
  const submitMutation = useSubmitReport();

  const reports: CommunityReport[] =
    (reportsData && "reports" in reportsData
      ? reportsData.reports
      : Array.isArray(reportsData)
        ? reportsData
        : []) ?? [];

  const canSubmit = incidentType && barangay && desc.length >= 10;

  const resetForm = useCallback(() => {
    setStep("form");
    setIncidentType("");
    setBarangay("");
    setDesc("");
    setPhoto(null);
  }, []);

  const handleSubmit = useCallback(() => {
    if (!canSubmit) return;

    const formData = new FormData();
    formData.append("barangay", barangay);
    formData.append("description", desc);
    formData.append(
      "risk_label",
      incidentType === "flooding" || incidentType === "road_closure"
        ? "Critical"
        : "Alert",
    );
    if (photo) formData.append("photo", photo);

    submitMutation.mutate(formData, {
      onSuccess: () => setStep("submitted"),
    });
  }, [canSubmit, barangay, desc, incidentType, photo, submitMutation]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith("image/") && f.size <= MAX_PHOTO_SIZE) {
      setPhoto(f);
    }
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f && f.size <= MAX_PHOTO_SIZE) setPhoto(f);
    },
    [],
  );

  // ── Submitted state ──
  if (step === "submitted") {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-6">
            <CheckCircle2 className="h-12 w-12 text-risk-safe mx-auto mb-3" />
            <div className="text-base font-bold text-risk-safe font-mono mb-1">
              Report Submitted
            </div>
            <p className="text-xs text-muted-foreground font-mono mb-4">
              Your report has been sent to the Parañaque City DRRMO.
            </p>
            <div className="inline-block rounded-lg border border-risk-safe/30 bg-risk-safe/5 px-4 py-2 mb-4">
              <div className="text-[9px] text-muted-foreground font-mono uppercase tracking-wider">
                Reference ID
              </div>
              <div className="text-sm text-risk-safe font-mono font-bold">
                {referenceId}
              </div>
            </div>
            <div>
              <Button variant="default" size="sm" onClick={resetForm}>
                Submit Another Report
              </Button>
            </div>
          </div>

          {/* Recent reports */}
          {reports.length > 0 && (
            <div className="border-t border-border mt-2 pt-4">
              <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-mono mb-2">
                Recent Community Reports
              </div>
              {reports.map((r) => (
                <ReportRow key={r.id} report={r} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // ── Form state ──
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-bold font-mono tracking-wide">
          <ClipboardList className="h-4 w-4" />
          Report Flood Incident
        </CardTitle>
        <Badge variant="outline" className="text-[9px] font-mono">
          {reportsLoading ? "..." : `${reports.length} recent reports`}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Incident type selector */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-mono mb-2">
            Incident Type *
          </div>
          <div className="flex flex-wrap gap-1.5">
            {INCIDENT_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setIncidentType(t.value)}
                className={cn(
                  "rounded-md border px-3 py-1.5 text-[11px] font-mono cursor-pointer transition-colors",
                  incidentType === t.value
                    ? t.color
                    : "text-muted-foreground border-border bg-muted hover:bg-accent/50",
                )}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Barangay */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-mono mb-2">
            Barangay *
          </div>
          <select
            value={barangay}
            onChange={(e) => setBarangay(e.target.value)}
            className={cn(
              "w-full rounded-md border border-border bg-muted px-3 py-2 text-xs font-mono outline-none transition-colors",
              barangay ? "text-foreground" : "text-muted-foreground",
            )}
          >
            <option value="">Select barangay…</option>
            {BARANGAY_NAMES.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-mono mb-2">
            Description * ({desc.length}/{MAX_DESC})
          </div>
          <textarea
            value={desc}
            onChange={(e) => setDesc(e.target.value.slice(0, MAX_DESC))}
            placeholder="Describe the flood condition - water depth, location landmarks, duration…"
            rows={3}
            className="w-full rounded-md border border-border bg-muted px-3 py-2 text-xs font-mono text-foreground placeholder:text-muted-foreground outline-none resize-y box-border"
          />
        </div>

        {/* Photo upload */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-mono mb-2">
            Photo Evidence (optional)
          </div>
          <div
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") fileRef.current?.click();
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            className={cn(
              "border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition-colors",
              isDragging && "border-primary bg-primary/5",
              photo && !isDragging && "border-risk-safe bg-risk-safe/5",
              !isDragging && !photo && "border-border bg-muted",
            )}
          >
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPTED_IMAGE_TYPES}
              className="hidden"
              onChange={handleFileChange}
            />
            {photo ? (
              <div className="space-y-1">
                <Upload className="h-5 w-5 mx-auto text-risk-safe" />
                <div className="text-[11px] text-risk-safe font-mono">
                  {photo.name}
                </div>
                <div className="text-[9px] text-muted-foreground font-mono">
                  {(photo.size / 1024).toFixed(0)} KB · Click to change
                </div>
              </div>
            ) : (
              <div className="space-y-1">
                <Camera className="h-6 w-6 mx-auto text-muted-foreground" />
                <div className="text-[11px] text-muted-foreground font-mono">
                  Drag & drop photo or click to browse
                </div>
                <div className="text-[9px] text-muted-foreground/60 font-mono">
                  JPG, PNG, WebP · Max 5 MB
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Submit */}
        <Button
          className="w-full font-mono"
          disabled={!canSubmit || submitMutation.isPending}
          onClick={handleSubmit}
        >
          {submitMutation.isPending
            ? "Submitting…"
            : canSubmit
              ? "Submit Report to DRRMO"
              : "Fill in required fields to submit"}
        </Button>
      </CardContent>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function CommunityReportsPanelSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-48" />
      </CardHeader>
      <CardContent className="space-y-4">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-9 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-10 w-full" />
      </CardContent>
    </Card>
  );
}
