/**
 * Admin AI Model Control Page
 *
 * ML model management: view current model info, performance metrics,
 * feature importance, version history, trigger retraining, rollback,
 * and real-time inference monitoring.
 */

import { PageHeader, SectionHeading } from "@/components/layout";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useModels,
  useRetrainStatus,
  useRollbackModel,
  useSystemHealth,
  useTriggerRetrain,
} from "@/features/admin/hooks/useAdmin";
import { useFeatureImportance } from "@/features/admin/hooks/useModel";
import {
  useModelHistory,
  type ModelVersionEntry,
} from "@/features/dashboard/hooks/useAnalytics";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { motion, useInView } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  BarChart3,
  Brain,
  CheckCircle,
  Clock,
  Download,
  Eye,
  FileCode,
  HardDrive,
  Hash,
  History,
  Loader2,
  RefreshCw,
  Shield,
  TrendingUp,
  XCircle,
  Zap,
} from "lucide-react";
import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";

// ── Helpers ──

function formatBytes(bytes: number): string {
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(2)} GB`;
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function formatPct(value: number): string {
  return value < 1 ? `${(value * 100).toFixed(1)}%` : value.toFixed(2);
}

const METRIC_LABELS: Record<string, string> = {
  accuracy: "Accuracy",
  f1_score: "F1 Score",
  f2_score: "F2 Score",
  precision: "Precision",
  recall: "Recall",
  cross_val_mean: "CV Mean",
  cross_val_std: "CV Std",
  cv_mean: "CV Mean",
  cv_std: "CV Std",
  roc_auc: "ROC AUC",
  log_loss: "Log Loss",
  mcc: "MCC",
  cohen_kappa: "Cohen Kappa",
};

function formatMetricLabel(key: string): string {
  return (
    METRIC_LABELS[key] ??
    key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

type AccentLevel = "good" | "warn" | "critical" | "neutral";

function accentGradient(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "from-risk-safe/60 via-risk-safe to-risk-safe/60";
    case "warn":
      return "from-risk-alert/60 via-risk-alert to-risk-alert/60";
    case "critical":
      return "from-risk-critical/60 via-risk-critical to-risk-critical/60";
    default:
      return "from-primary/40 via-primary/60 to-primary/40";
  }
}

function statTextColor(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "text-risk-safe";
    case "warn":
      return "text-risk-alert";
    case "critical":
      return "text-risk-critical";
    default:
      return "";
  }
}

function iconRing(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "bg-risk-safe/10 ring-risk-safe/20";
    case "warn":
      return "bg-risk-alert/10 ring-risk-alert/20";
    case "critical":
      return "bg-risk-critical/10 ring-risk-critical/20";
    default:
      return "bg-primary/10 ring-primary/20";
  }
}

// ── Stat Card ──

function StatCard({
  icon: Icon,
  label,
  value,
  isLoading,
  health = "neutral",
  description,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  isLoading?: boolean;
  health?: AccentLevel;
  description?: string;
}) {
  return (
    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
      <div
        className={cn("h-1 w-full bg-linear-to-r", accentGradient(health))}
      />
      <div className="pt-4 pb-3 px-6 flex items-center gap-3">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl ring-1",
            iconRing(health),
          )}
        >
          <Icon
            className={cn(
              "h-5 w-5",
              health === "neutral" ? "text-primary" : statTextColor(health),
            )}
          />
        </div>
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{label}</p>
          {isLoading ? (
            <Skeleton className="h-7 w-20 mt-0.5" />
          ) : (
            <p
              className={cn(
                "text-2xl font-bold truncate",
                statTextColor(health),
              )}
            >
              {value}
            </p>
          )}
          {description && (
            <p className="text-[10px] text-muted-foreground/70">
              {description}
            </p>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

// ── Detail Row ──

function DetailRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between text-sm py-1.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-right max-w-[60%] truncate">
        {children}
      </span>
    </div>
  );
}

// ── Component ──

export default function AdminModelsPage() {
  const queryClient = useQueryClient();

  const [retrainDialogOpen, setRetrainDialogOpen] = useState(false);
  const [rollbackDialogOpen, setRollbackDialogOpen] = useState(false);
  const [rollbackVersion, setRollbackVersion] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [expandedVersion, setExpandedVersion] = useState<number | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // ── Queries ──
  const { data: health, isLoading: healthLoading } = useSystemHealth();
  const { isLoading: modelsLoading } = useModels();
  const { data: historyData, isLoading: historyLoading } = useModelHistory();
  const { data: importanceData, isLoading: importanceLoading } =
    useFeatureImportance();
  const modelVersions = useMemo(
    () => historyData?.models ?? [],
    [historyData?.models],
  );
  const retrainStatus = useRetrainStatus(taskId);
  const triggerRetrain = useTriggerRetrain();
  const rollback = useRollbackModel();

  const model = health?.model;
  const modelLoaded = health?.checks?.model_available ?? false;

  // ── Derived ──

  const latestTrainedVersion = useMemo(() => {
    if (!modelVersions.length) return null;
    return Math.max(...modelVersions.map((mv) => mv.version));
  }, [modelVersions]);

  const versionMismatch =
    model?.version != null &&
    latestTrainedVersion != null &&
    Number(model.version) < latestTrainedVersion;

  const activeVersion = useMemo(
    () => modelVersions.find((mv) => mv.is_active),
    [modelVersions],
  );

  // Sorted feature importance data
  const sortedFeatures = useMemo(
    () =>
      importanceData?.features
        ? [...importanceData.features].sort(
            (a, b) => b.importance - a.importance,
          )
        : [],
    [importanceData],
  );

  const maxImportance = sortedFeatures[0]?.importance ?? 1;

  // ── Handlers ──

  const refreshAll = useCallback(async () => {
    setIsRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: ["admin"] });
    await queryClient.invalidateQueries({ queryKey: ["analytics"] });
    await queryClient.invalidateQueries({ queryKey: ["model"] });
    setIsRefreshing(false);
  }, [queryClient]);

  const handleRetrain = useCallback(() => {
    triggerRetrain.mutate(undefined, {
      onSuccess: (res) => {
        const tid = res.data?.task_id;
        if (tid) setTaskId(tid);
        toast.success("Retraining job queued successfully");
        setRetrainDialogOpen(false);
      },
      onError: () => toast.error("Failed to queue retraining job"),
    });
  }, [triggerRetrain]);

  const handleRollback = useCallback(() => {
    if (!rollbackVersion.trim()) {
      toast.error("Please select a version to rollback to");
      return;
    }
    rollback.mutate(rollbackVersion.trim(), {
      onSuccess: (res) => {
        toast.success(res.message || `Rolled back to ${rollbackVersion}`);
        setRollbackDialogOpen(false);
        setRollbackVersion("");
        queryClient.invalidateQueries({ queryKey: ["admin"] });
        queryClient.invalidateQueries({ queryKey: ["analytics"] });
      },
      onError: () => toast.error("Rollback failed"),
    });
  }, [rollback, rollbackVersion, queryClient]);

  // ── Animation refs ──
  const statusRef = useRef<HTMLDivElement>(null);
  const statusInView = useInView(statusRef, { once: true, amount: 0.1 });
  const detailsRef = useRef<HTMLDivElement>(null);
  const detailsInView = useInView(detailsRef, { once: true, amount: 0.1 });
  const importanceRef = useRef<HTMLDivElement>(null);
  const importanceInView = useInView(importanceRef, {
    once: true,
    amount: 0.1,
  });
  const versionsRef = useRef<HTMLDivElement>(null);
  const versionsInView = useInView(versionsRef, { once: true, amount: 0.1 });

  // ── Clear taskId on retrain complete/fail ──
  const retrainStatusValue = retrainStatus.data?.data?.status;
  const prevStatusRef = useRef(retrainStatusValue);
  useEffect(() => {
    if (prevStatusRef.current === retrainStatusValue) return;
    prevStatusRef.current = retrainStatusValue;
    if (retrainStatusValue === "completed") {
      toast.success("Model retraining completed successfully");
      startTransition(() => setTaskId(null));
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
      queryClient.invalidateQueries({ queryKey: ["model"] });
    } else if (retrainStatusValue === "failed") {
      toast.error(retrainStatus.data?.data?.message ?? "Retraining failed");
      startTransition(() => setTaskId(null));
    }
  }, [retrainStatusValue, retrainStatus.data?.data?.message, queryClient]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <Breadcrumb
          items={[{ label: "Admin", href: "/admin" }, { label: "ML Models" }]}
          className="mb-4"
        />
        <div className="flex items-start justify-between">
          <PageHeader
            icon={Brain}
            title="AI Model Control"
            subtitle="Manage the Random Forest flood prediction model"
          />
          <div className="flex items-center gap-2 pt-1">
            <Button
              variant="outline"
              size="sm"
              onClick={refreshAll}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={cn("h-4 w-4 mr-1.5", isRefreshing && "animate-spin")}
              />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRollbackDialogOpen(true)}
              disabled={rollback.isPending}
            >
              <ArrowDownToLine className="h-4 w-4 mr-1.5" />
              Rollback
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={() => setRetrainDialogOpen(true)}
              disabled={triggerRetrain.isPending}
            >
              <RefreshCw className="h-4 w-4 mr-1.5" />
              Retrain Model
            </Button>
          </div>
        </div>
      </div>

      {/* Version Mismatch Banner */}
      {versionMismatch && (
        <div className="w-full px-6 mt-4">
          <div className="rounded-lg border border-risk-alert/40 bg-risk-alert/5 px-4 py-3 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-risk-alert shrink-0" />
            <div>
              <p className="text-sm font-medium text-risk-alert">
                Model Version Mismatch
              </p>
              <p className="text-xs text-muted-foreground">
                Loaded model is v{model?.version} but the latest trained version
                is v{latestTrainedVersion}. Deploy the new version or rollback.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Model Status Panel ── */}
      <section className="py-6 bg-muted/30">
        <div className="w-full px-6" ref={statusRef}>
          <SectionHeading
            label="Overview"
            title="Model Status"
            subtitle="Current model availability, type, version, and feature count"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={statusInView ? "show" : undefined}
            className="grid gap-4 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
          >
            <motion.div variants={fadeUp}>
              <StatCard
                icon={modelLoaded ? CheckCircle : XCircle}
                label="Status"
                value={
                  healthLoading ? "" : modelLoaded ? "Loaded" : "Unavailable"
                }
                isLoading={healthLoading}
                health={modelLoaded ? "good" : "critical"}
              />
            </motion.div>
            <motion.div variants={fadeUp}>
              <StatCard
                icon={Activity}
                label="Model Type"
                value={model?.type ?? "N/A"}
                isLoading={healthLoading}
              />
            </motion.div>
            <motion.div variants={fadeUp}>
              <StatCard
                icon={Clock}
                label="Version"
                value={model?.version ? `v${model.version}` : "N/A"}
                isLoading={healthLoading}
                health={versionMismatch ? "warn" : "neutral"}
                description={versionMismatch ? "Update available" : undefined}
              />
            </motion.div>
            <motion.div variants={fadeUp}>
              <StatCard
                icon={Brain}
                label="Input Features"
                value={model?.features_count ?? "N/A"}
                isLoading={healthLoading}
              />
            </motion.div>
            <motion.div variants={fadeUp}>
              <StatCard
                icon={HardDrive}
                label="Model Size"
                value={
                  model?.file_size_bytes
                    ? formatBytes(model.file_size_bytes)
                    : "N/A"
                }
                isLoading={healthLoading}
              />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Performance Metrics & Model Details ── */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={detailsRef}>
          <SectionHeading
            label="Performance"
            title="Metrics & Details"
            subtitle="Model accuracy scores, configuration, and training task status"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={detailsInView ? "show" : undefined}
            className="space-y-6"
          >
            {/* Performance Metrics */}
            {model?.metrics && Object.keys(model.metrics).length > 0 && (
              <motion.div variants={fadeUp}>
                <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                  <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                        <TrendingUp className="h-4 w-4 text-primary" />
                      </div>
                      Performance Metrics
                    </CardTitle>
                    <CardDescription>
                      Current production model (v{model.version}) metrics from
                      held-out test set evaluation
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
                      {Object.entries(model.metrics).map(([key, value]) => {
                        const isHighCV =
                          key === "cv_std" &&
                          typeof value === "number" &&
                          value > 0.05;
                        const isPerfect =
                          typeof value === "number" &&
                          value >= 0.999 &&
                          key !== "cv_std";
                        return (
                          <div
                            key={key}
                            className={cn(
                              "space-y-1 p-3 rounded-lg",
                              isHighCV
                                ? "bg-risk-alert/5 ring-1 ring-risk-alert/20"
                                : isPerfect
                                  ? "bg-risk-alert/5 ring-1 ring-risk-alert/20"
                                  : "bg-muted/30",
                            )}
                          >
                            <div className="flex items-center gap-1.5">
                              <p className="text-sm text-muted-foreground">
                                {formatMetricLabel(key)}
                              </p>
                              {isHighCV && (
                                <AlertTriangle className="h-3 w-3 text-risk-alert" />
                              )}
                              {isPerfect && (
                                <AlertTriangle className="h-3 w-3 text-risk-alert" />
                              )}
                            </div>
                            <p className="text-2xl font-bold">
                              {typeof value === "number"
                                ? formatPct(value)
                                : String(value)}
                            </p>
                            {isHighCV && (
                              <p className="text-[10px] text-risk-alert">
                                High variance across folds
                              </p>
                            )}
                            {isPerfect && (
                              <p className="text-[10px] text-risk-alert">
                                Suspiciously high - verify no data leakage
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Cross-validation details */}
                    {activeVersion?.cross_validation && (
                      <div className="mt-4 pt-4 border-t">
                        <p className="text-xs text-muted-foreground mb-2">
                          Cross-Validation:{" "}
                          {activeVersion.cross_validation.cv_folds}-fold CV mean{" "}
                          {(
                            (activeVersion.cross_validation.cv_mean ?? 0) * 100
                          ).toFixed(1)}
                          % ±{" "}
                          {(
                            (activeVersion.cross_validation.cv_std ?? 0) * 100
                          ).toFixed(1)}
                          %
                        </p>
                      </div>
                    )}
                  </CardContent>
                </GlassCard>
              </motion.div>
            )}

            {/* Model Details */}
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                      <Brain className="h-4 w-4 text-primary" />
                    </div>
                    Model Details
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {modelsLoading || healthLoading ? (
                    <div className="space-y-3">
                      {Array.from({ length: 6 }).map((_, i) => (
                        <Skeleton key={i} className="h-5 w-full" />
                      ))}
                    </div>
                  ) : (
                    <div className="grid gap-x-8 gap-y-1 sm:grid-cols-2">
                      <DetailRow label="Created">
                        {model?.created_at
                          ? new Date(model.created_at).toLocaleString("en-PH", {
                              dateStyle: "medium",
                              timeStyle: "short",
                            })
                          : "N/A"}
                      </DetailRow>
                      <DetailRow label="Feature Count">
                        {model?.features_count ?? "N/A"}
                      </DetailRow>
                      <DetailRow label="Model File">
                        <span className="font-mono text-xs">
                          {model?.model_file ?? "N/A"}
                        </span>
                      </DetailRow>
                      <DetailRow label="File Size">
                        {model?.file_size_bytes
                          ? formatBytes(model.file_size_bytes)
                          : "N/A"}
                      </DetailRow>
                      <DetailRow label="Training Dataset">
                        {model?.training_data?.total_records
                          ? `${model.training_data.total_records.toLocaleString()} records`
                          : "N/A"}
                      </DetailRow>
                      <DetailRow label="SHA-256 Checksum">
                        {model?.checksum ? (
                          <span
                            className="font-mono text-[10px] truncate max-w-50 inline-block"
                            title={model.checksum}
                          >
                            {model.checksum.slice(0, 16)}…
                          </span>
                        ) : (
                          "N/A"
                        )}
                      </DetailRow>
                      <DetailRow label="Inference Status">
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs",
                            modelLoaded
                              ? "bg-risk-safe/10 text-risk-safe border-risk-safe/30"
                              : "bg-risk-critical/10 text-risk-critical border-risk-critical/30",
                          )}
                        >
                          {modelLoaded ? (
                            <>
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Ready
                            </>
                          ) : (
                            <>
                              <XCircle className="h-3 w-3 mr-1" />
                              Not Loaded
                            </>
                          )}
                        </Badge>
                      </DetailRow>
                      <DetailRow label="Health">
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs",
                            health?.status === "healthy"
                              ? "bg-risk-safe/10 text-risk-safe border-risk-safe/30"
                              : "bg-risk-alert/10 text-risk-alert border-risk-alert/30",
                          )}
                        >
                          {health?.status === "healthy"
                            ? "Healthy"
                            : "Degraded"}
                        </Badge>
                      </DetailRow>
                    </div>
                  )}
                </CardContent>
              </GlassCard>
            </motion.div>

            {/* Retraining Progress */}
            {taskId && (
              <motion.div variants={fadeUp}>
                <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                  <div className="h-1 w-full bg-linear-to-r from-risk-alert/60 via-risk-alert to-risk-alert/60" />
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-risk-alert/10 ring-1 ring-risk-alert/20">
                        <Loader2 className="h-4 w-4 animate-spin text-risk-alert" />
                      </div>
                      Retraining in Progress
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span className="font-mono">{taskId}</span>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs capitalize",
                            retrainStatusValue === "training"
                              ? "bg-primary/10 text-primary border-primary/30"
                              : retrainStatusValue === "validating"
                                ? "bg-risk-alert/15 text-risk-alert border-risk-alert/30"
                                : retrainStatusValue === "completed"
                                  ? "bg-risk-safe/10 text-risk-safe border-risk-safe/30"
                                  : "bg-muted text-muted-foreground",
                          )}
                        >
                          {retrainStatusValue ?? "queued"}
                        </Badge>
                      </div>
                      <div className="h-2.5 w-full rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary transition-all duration-700 ease-out"
                          style={{
                            width:
                              retrainStatusValue === "training"
                                ? "60%"
                                : retrainStatusValue === "validating"
                                  ? "85%"
                                  : retrainStatusValue === "completed"
                                    ? "100%"
                                    : "20%",
                          }}
                        />
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Zap className="h-3 w-3" />
                          {retrainStatusValue === "training"
                            ? "Training model…"
                            : retrainStatusValue === "validating"
                              ? "Evaluating performance…"
                              : retrainStatusValue === "completed"
                                ? "Complete!"
                                : "Queued - waiting for worker"}
                        </span>
                      </div>
                    </div>
                    {retrainStatus.data?.data?.message && (
                      <p className="text-xs text-muted-foreground border-t pt-2">
                        {retrainStatus.data.data.message}
                      </p>
                    )}
                  </CardContent>
                </GlassCard>
              </motion.div>
            )}
          </motion.div>
        </div>
      </section>

      {/* ── Feature Importance ── */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={importanceRef}>
          <SectionHeading
            label="Features"
            title="Feature Importance"
            subtitle="Ranked contribution of each input feature to the model's predictions"
          />
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={importanceInView ? "show" : undefined}
          >
            <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
              <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                    <BarChart3 className="h-4 w-4 text-primary" />
                  </div>
                  Feature Ranking
                  {importanceData?.model_version && (
                    <Badge variant="outline" className="ml-auto text-xs">
                      v{importanceData.model_version}
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription>
                  Extracted from the trained model's{" "}
                  <code className="text-xs">feature_importances_</code>{" "}
                  attribute
                </CardDescription>
              </CardHeader>
              <CardContent>
                {importanceLoading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 8 }).map((_, i) => (
                      <Skeleton
                        key={`fi-skel-${i}`}
                        className="h-8 w-full rounded"
                      />
                    ))}
                  </div>
                ) : sortedFeatures.length > 0 ? (
                  <div className="space-y-2">
                    {sortedFeatures.map((f, idx) => {
                      const pct = (f.importance / maxImportance) * 100;
                      return (
                        <div key={f.feature} className="group">
                          <div className="flex items-center gap-3">
                            <span className="w-5 text-right text-xs text-muted-foreground font-mono">
                              {idx + 1}
                            </span>
                            <span className="w-48 text-sm font-medium truncate">
                              {f.feature.replace(/_/g, " ")}
                            </span>
                            <div className="flex-1 h-6 rounded bg-muted/30 overflow-hidden relative">
                              <div
                                className={cn(
                                  "h-full rounded transition-all duration-500",
                                  idx === 0
                                    ? "bg-primary"
                                    : idx < 3
                                      ? "bg-primary/80"
                                      : "bg-primary/50",
                                )}
                                style={{ width: `${Math.max(pct, 2)}%` }}
                              />
                            </div>
                            <span className="w-16 text-right text-xs font-mono text-muted-foreground">
                              {(f.importance * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    Feature importance data not available
                  </p>
                )}
              </CardContent>
            </GlassCard>
          </motion.div>
        </div>
      </section>

      {/* ── Version History ── */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={versionsRef}>
          <SectionHeading
            label="History"
            title="Model Versions"
            subtitle="Progressive training history from v1 baseline to production"
          />
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={versionsInView ? "show" : undefined}
          >
            <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
              <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                    <History className="h-4 w-4 text-primary" />
                  </div>
                  Version Timeline
                </CardTitle>
                <CardDescription>
                  Each version trained progressively with expanded data and
                  features
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-28">Version</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead className="text-right">Accuracy</TableHead>
                        <TableHead className="text-right">F1</TableHead>
                        <TableHead className="text-right">ROC AUC</TableHead>
                        <TableHead className="text-right">CV Mean</TableHead>
                        <TableHead className="text-right">Samples</TableHead>
                        <TableHead className="text-right">Size</TableHead>
                        <TableHead className="text-center w-28">
                          Actions
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {historyLoading ? (
                        <TableRow>
                          <TableCell
                            colSpan={9}
                            className="text-center py-8 text-muted-foreground"
                          >
                            <Loader2 className="h-4 w-4 animate-spin inline mr-2" />
                            Loading model history…
                          </TableCell>
                        </TableRow>
                      ) : modelVersions.length === 0 ? (
                        <TableRow>
                          <TableCell
                            colSpan={9}
                            className="text-center py-8 text-muted-foreground"
                          >
                            No model versions found
                          </TableCell>
                        </TableRow>
                      ) : (
                        modelVersions.map((mv) => {
                          const isPerfect = mv.metrics.accuracy >= 0.999;
                          const isLow = mv.metrics.accuracy < 0.7;
                          return (
                            <VersionRow
                              key={mv.version}
                              mv={mv}
                              isPerfect={isPerfect}
                              isLow={isLow}
                              expanded={expandedVersion === mv.version}
                              onToggleExpand={() =>
                                setExpandedVersion(
                                  expandedVersion === mv.version
                                    ? null
                                    : mv.version,
                                )
                              }
                              onRollback={() => {
                                setRollbackVersion(`v${mv.version}`);
                                setRollbackDialogOpen(true);
                              }}
                            />
                          );
                        })
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </GlassCard>
          </motion.div>
        </div>
      </section>

      {/* ── Retrain Confirmation Dialog ── */}
      <AlertDialog open={retrainDialogOpen} onOpenChange={setRetrainDialogOpen}>
        <AlertDialogContent className="max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5 text-primary" />
              Retrain Model
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3">
                <p>
                  This will queue a full retraining of the Random Forest model
                  using the latest ingested weather data. The current production
                  model (v{model?.version ?? "?"}) will remain active until the
                  new version is reviewed and deployed.
                </p>
                {activeVersion && (
                  <div className="rounded-lg bg-muted/50 p-3 text-xs space-y-1">
                    <p className="font-medium text-foreground">
                      Current Model Configuration
                    </p>
                    <p>
                      Training data:{" "}
                      {activeVersion.training_data.total_records.toLocaleString()}{" "}
                      records
                    </p>
                    <p>Features: {activeVersion.features.length}</p>
                    <p>
                      Algorithm:{" "}
                      {activeVersion.model_type ?? "RandomForestClassifier"}
                    </p>
                  </div>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRetrain}
              disabled={triggerRetrain.isPending}
            >
              {triggerRetrain.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Start Retraining
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* ── Rollback Dialog ── */}
      <AlertDialog
        open={rollbackDialogOpen}
        onOpenChange={setRollbackDialogOpen}
      >
        <AlertDialogContent className="max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-risk-alert">
              <ArrowDownToLine className="h-5 w-5" />
              Rollback Model
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3">
                <p>
                  Rolling back will replace the current production model. This
                  affects all live flood predictions immediately.
                </p>
                {model?.version && (
                  <p className="text-xs">
                    Current production: <strong>v{model.version}</strong>
                  </p>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="px-6 pb-2 space-y-3">
            <div>
              <Label htmlFor="rollback-version" className="text-sm">
                Select version to rollback to
              </Label>
              <Select
                value={rollbackVersion}
                onValueChange={setRollbackVersion}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Choose a version…" />
                </SelectTrigger>
                <SelectContent>
                  {modelVersions
                    .filter((mv) => !mv.is_active)
                    .sort((a, b) => b.version - a.version)
                    .map((mv) => (
                      <SelectItem key={mv.version} value={`v${mv.version}`}>
                        v{mv.version} - {mv.name} (
                        {(mv.metrics.accuracy * 100).toFixed(1)}% acc)
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>

            {/* Side-by-side comparison */}
            {rollbackVersion && activeVersion && (
              <RollbackComparison
                current={activeVersion}
                target={modelVersions.find(
                  (mv) => `v${mv.version}` === rollbackVersion,
                )}
              />
            )}
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setRollbackVersion("")}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRollback}
              disabled={rollback.isPending || !rollbackVersion.trim()}
              className="bg-risk-alert hover:bg-risk-alert/90"
            >
              {rollback.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Confirm Rollback
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ── Version Row ──

function VersionRow({
  mv,
  isPerfect,
  isLow,
  expanded,
  onToggleExpand,
  onRollback,
}: {
  mv: ModelVersionEntry;
  isPerfect: boolean;
  isLow: boolean;
  expanded: boolean;
  onToggleExpand: () => void;
  onRollback: () => void;
}) {
  const metricClass = (val: number) =>
    cn(
      "text-right font-mono text-sm",
      val >= 0.999
        ? "text-risk-alert font-semibold"
        : val < 0.7
          ? "text-risk-critical"
          : "",
    );

  return (
    <>
      <TableRow
        className={cn(
          mv.is_active && "bg-primary/5",
          isPerfect && "bg-risk-alert/3",
          isLow && "bg-risk-critical/3",
        )}
      >
        <TableCell className="font-mono font-medium">
          <div className="flex items-center gap-1.5">
            v{mv.version}
            {mv.is_active && (
              <Badge variant="default" className="text-[10px] px-1.5 py-0">
                prod
              </Badge>
            )}
            {isPerfect && !mv.is_active && (
              <AlertTriangle className="h-3 w-3 text-risk-alert" />
            )}
          </div>
        </TableCell>
        <TableCell>
          <div>
            <p className="text-sm font-medium">{mv.name}</p>
            <p className="text-xs text-muted-foreground line-clamp-1">
              {mv.description}
            </p>
          </div>
        </TableCell>
        <TableCell className={metricClass(mv.metrics.accuracy)}>
          {(mv.metrics.accuracy * 100).toFixed(1)}%
        </TableCell>
        <TableCell className={metricClass(mv.metrics.f1_score)}>
          {(mv.metrics.f1_score * 100).toFixed(1)}%
        </TableCell>
        <TableCell className="text-right font-mono text-sm">
          {(mv.metrics.roc_auc * 100).toFixed(1)}%
        </TableCell>
        <TableCell className="text-right font-mono text-sm">
          {((mv.cross_validation?.cv_mean ?? mv.metrics.cv_mean) * 100).toFixed(
            1,
          )}
          %
        </TableCell>
        <TableCell className="text-right text-sm">
          {mv.training_data.total_records.toLocaleString()}
        </TableCell>
        <TableCell className="text-right text-xs text-muted-foreground">
          {mv.file_size_bytes ? formatBytes(mv.file_size_bytes) : "-"}
        </TableCell>
        <TableCell className="text-center">
          <div className="flex items-center justify-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onToggleExpand}
              title="View details"
            >
              <Eye className="h-3.5 w-3.5" />
            </Button>
            {!mv.is_active && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-risk-alert hover:text-risk-alert"
                onClick={onRollback}
                title="Rollback to this version"
              >
                <ArrowDownToLine className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </TableCell>
      </TableRow>
      {expanded && (
        <TableRow>
          <TableCell colSpan={9} className="bg-muted/20 p-0">
            <VersionDetail mv={mv} isPerfect={isPerfect} isLow={isLow} />
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

// ── Expanded Version Detail ──

function VersionDetail({
  mv,
  isPerfect,
  isLow,
}: {
  mv: ModelVersionEntry;
  isPerfect: boolean;
  isLow: boolean;
}) {
  return (
    <div className="p-5 space-y-4">
      {/* Warning banners */}
      {isPerfect && (
        <div className="rounded-lg border border-risk-alert/40 bg-risk-alert/5 px-3 py-2 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-risk-alert shrink-0 mt-0.5" />
          <div className="text-xs">
            <p className="font-medium text-risk-alert">
              Suspicious 100% Metrics
            </p>
            <p className="text-muted-foreground">
              Perfect accuracy on real-world flood data is implausible. This
              likely indicates data leakage, overfitting, or an improper
              train/test split. Retrain with proper stratified sampling before
              relying on this version.
            </p>
          </div>
        </div>
      )}
      {isLow && (
        <div className="rounded-lg border border-risk-critical/40 bg-risk-critical/5 px-3 py-2 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-risk-critical shrink-0 mt-0.5" />
          <div className="text-xs">
            <p className="font-medium text-risk-critical">
              Significant Performance Drop
            </p>
            <p className="text-muted-foreground">
              This version shows a notable accuracy degradation. Investigate
              training data quality, feature engineering changes, or class
              distribution shifts.
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        {/* Full Metrics */}
        <div>
          <h4 className="text-sm font-medium mb-2 flex items-center gap-1.5">
            <TrendingUp className="h-3.5 w-3.5 text-primary" />
            All Metrics
          </h4>
          <div className="space-y-1">
            {Object.entries(mv.metrics).map(([key, value]) => (
              <div key={key} className="flex justify-between text-xs">
                <span className="text-muted-foreground">
                  {formatMetricLabel(key)}
                </span>
                <span className="font-mono font-medium">
                  {formatPct(value)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Training Info */}
        <div>
          <h4 className="text-sm font-medium mb-2 flex items-center gap-1.5">
            <FileCode className="h-3.5 w-3.5 text-primary" />
            Training Info
          </h4>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Trained</span>
              <span>
                {mv.created_at
                  ? formatDistanceToNow(new Date(mv.created_at), {
                      addSuffix: true,
                    })
                  : "N/A"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Records</span>
              <span>{mv.training_data.total_records.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Features</span>
              <span>{mv.training_data.num_features}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Model Type</span>
              <span>{mv.model_type ?? "RandomForestClassifier"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">File Size</span>
              <span>
                {mv.file_size_bytes ? formatBytes(mv.file_size_bytes) : "-"}
              </span>
            </div>
            {mv.checksum && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Checksum</span>
                <span
                  className="font-mono truncate max-w-30"
                  title={mv.checksum}
                >
                  {mv.checksum.slice(0, 12)}…
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Cross-Validation & Parameters */}
        <div>
          <h4 className="text-sm font-medium mb-2 flex items-center gap-1.5">
            <Shield className="h-3.5 w-3.5 text-primary" />
            CV & Parameters
          </h4>
          <div className="space-y-1 text-xs">
            {mv.cross_validation && (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">CV Folds</span>
                  <span>{mv.cross_validation.cv_folds ?? "N/A"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">CV Mean</span>
                  <span className="font-mono">
                    {mv.cross_validation.cv_mean != null
                      ? formatPct(mv.cross_validation.cv_mean)
                      : "N/A"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">CV Std</span>
                  <span
                    className={cn(
                      "font-mono",
                      (mv.cross_validation.cv_std ?? 0) > 0.05 &&
                        "text-risk-alert",
                    )}
                  >
                    {mv.cross_validation.cv_std != null
                      ? formatPct(mv.cross_validation.cv_std)
                      : "N/A"}
                  </span>
                </div>
              </>
            )}
            <Separator className="my-1.5" />
            {mv.model_parameters &&
            Object.keys(mv.model_parameters).length > 0 ? (
              Object.entries(mv.model_parameters)
                .slice(0, 6)
                .map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-muted-foreground">{k}</span>
                    <span className="font-mono">{String(v)}</span>
                  </div>
                ))
            ) : (
              <p className="text-muted-foreground italic">
                No parameters recorded
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Feature List */}
      {mv.features.length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-2 flex items-center gap-1.5">
            <Hash className="h-3.5 w-3.5 text-primary" />
            Features ({mv.features.length})
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {mv.features.map((f) => (
              <Badge key={f} variant="outline" className="text-[10px]">
                {f}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Data Sources */}
      {mv.training_data.files && mv.training_data.files.length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-2 flex items-center gap-1.5">
            <Download className="h-3.5 w-3.5 text-primary" />
            Training Data Sources
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {mv.training_data.files.map((f) => (
              <Badge
                key={f}
                variant="secondary"
                className="text-[10px] font-mono"
              >
                {f}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Rollback Comparison ──

function RollbackComparison({
  current,
  target,
}: {
  current: ModelVersionEntry;
  target: ModelVersionEntry | undefined;
}) {
  if (!target) return null;

  const metrics: { key: keyof ModelVersionEntry["metrics"]; label: string }[] =
    [
      { key: "accuracy", label: "Accuracy" },
      { key: "f1_score", label: "F1 Score" },
      { key: "precision", label: "Precision" },
      { key: "recall", label: "Recall" },
      { key: "roc_auc", label: "ROC AUC" },
    ];

  const targetWorse = metrics.some(
    ({ key }) => target.metrics[key] < current.metrics[key] - 0.01,
  );

  return (
    <div className="space-y-2">
      <div className="rounded-lg border p-3">
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div />
          <div className="text-center font-medium">
            Current (v{current.version})
          </div>
          <div className="text-center font-medium">
            Target (v{target.version})
          </div>
          {metrics.map(({ key, label }) => {
            const cVal = current.metrics[key];
            const tVal = target.metrics[key];
            const worse = tVal < cVal - 0.005;
            return (
              <div key={key} className="contents">
                <div className="text-muted-foreground">{label}</div>
                <div className="text-center font-mono">{formatPct(cVal)}</div>
                <div
                  className={cn(
                    "text-center font-mono",
                    worse && "text-risk-critical font-semibold",
                  )}
                >
                  {formatPct(tVal)}
                  {worse && " ↓"}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      {targetWorse && (
        <div className="rounded-lg border border-risk-alert/40 bg-risk-alert/5 px-3 py-2 flex items-center gap-2 text-xs">
          <AlertTriangle className="h-3.5 w-3.5 text-risk-alert shrink-0" />
          <p className="text-risk-alert">
            The target version performs worse on some key metrics. Proceed with
            caution.
          </p>
        </div>
      )}
    </div>
  );
}
