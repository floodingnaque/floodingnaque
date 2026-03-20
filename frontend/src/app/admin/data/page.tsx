/**
 * Admin Dataset Management Page
 *
 * Upload, validate, and ingest CSV/Excel weather data. Export weather,
 * predictions, and alert data with date-range & source filters. Shows
 * live dataset overview stats and a validation/upload pipeline with
 * drag-and-drop, preview, and progress feedback.
 */

import { PageHeader, SectionHeading } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
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
  datasetQueryKeys,
  useAlertsCount,
  useDatasetStats,
  usePredictionsCount,
  useWeatherCount,
} from "@/features/admin/hooks/useDataset";
import {
  datasetApi,
  type UploadResult,
  type ValidationResult,
} from "@/features/admin/services/datasetApi";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { format, formatDistanceToNow, subDays } from "date-fns";
import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  Calendar,
  CheckCircle,
  Clock,
  CloudRain,
  Database,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  Loader2,
  RefreshCw,
  Server,
  Trash2,
  Upload,
  UploadCloud,
  XCircle,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

// ── Constants ──

const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ACCEPTED_TYPES = [".csv", ".xlsx", ".xls"];

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

function formatFileSize(bytes: number): string {
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function formatDateInput(d: Date): string {
  return format(d, "yyyy-MM-dd");
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
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          {isLoading ? (
            <Skeleton className="h-7 w-20 mt-0.5" />
          ) : (
            <p className={cn("text-2xl font-bold", statTextColor(health))}>
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

// ── File Drop Zone ──

function FileDropZone({
  onFileSelect,
  disabled,
}: {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      const file = e.dataTransfer.files[0];
      if (file) onFileSelect(file);
    },
    [disabled, onFileSelect],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileSelect(file);
      if (inputRef.current) inputRef.current.value = "";
    },
    [onFileSelect],
  );

  return (
    <div
      className={cn(
        "relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-all cursor-pointer",
        dragOver
          ? "border-primary bg-primary/5"
          : "border-muted-foreground/20 hover:border-primary/50 hover:bg-muted/30",
        disabled && "opacity-50 cursor-not-allowed",
      )}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      role="button"
      tabIndex={disabled ? -1 : 0}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(",")}
        onChange={handleChange}
        className="hidden"
        aria-label="Upload weather data file"
      />
      <UploadCloud
        className={cn(
          "h-10 w-10 mb-3",
          dragOver ? "text-primary" : "text-muted-foreground/40",
        )}
      />
      <p className="text-sm font-medium">
        Drag & drop your file here, or{" "}
        <span className="text-primary underline">browse</span>
      </p>
      <p className="text-xs text-muted-foreground mt-1">
        CSV, Excel (.xlsx, .xls) — max {MAX_FILE_SIZE_MB}MB
      </p>
    </div>
  );
}

// ── Export Card ──

function ExportCard({
  title,
  icon: Icon,
  description,
  count,
  countLoading,
  exporting,
  onExport,
  filterContent,
}: {
  title: string;
  icon: React.ElementType;
  description: string;
  count: number | undefined;
  countLoading: boolean;
  exporting: boolean;
  onExport: () => void;
  filterContent: React.ReactNode;
}) {
  return (
    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
      <div className="h-1 w-full bg-linear-to-r from-primary/40 via-primary/60 to-primary/40" />
      <div className="pt-5 px-5 pb-5 space-y-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
            <Icon className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="text-sm font-medium">{title}</p>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
        </div>

        {filterContent}

        <Separator />

        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {countLoading ? (
              <Skeleton className="h-4 w-32 inline-block" />
            ) : count != null ? (
              `Approx. ${count.toLocaleString()} records`
            ) : (
              "Count unavailable"
            )}
          </p>
          <Button size="sm" onClick={onExport} disabled={exporting}>
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
            ) : (
              <Download className="h-4 w-4 mr-1.5" />
            )}
            Export CSV
          </Button>
        </div>
      </div>
    </GlassCard>
  );
}

// ── Date Preset Buttons ──

function DatePresets({
  onSelect,
}: {
  onSelect: (start: string, end: string) => void;
}) {
  const today = new Date();
  return (
    <div className="flex gap-1.5 flex-wrap">
      {[
        { label: "7d", days: 7 },
        { label: "30d", days: 30 },
        { label: "90d", days: 90 },
      ].map(({ label, days }) => (
        <Button
          key={label}
          variant="outline"
          size="sm"
          className="h-7 text-xs px-2"
          onClick={() =>
            onSelect(
              formatDateInput(subDays(today, days)),
              formatDateInput(today),
            )
          }
        >
          {label}
        </Button>
      ))}
    </div>
  );
}

// ── Main Component ──

export default function AdminDataPage() {
  // ── Upload state ──
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);

  // ── Export filter state ──
  const [wxStart, setWxStart] = useState("");
  const [wxEnd, setWxEnd] = useState("");
  const [wxSource, setWxSource] = useState("all");
  const [predStart, setPredStart] = useState("");
  const [predEnd, setPredEnd] = useState("");
  const [predRisk, setPredRisk] = useState("all");
  const [alertStart, setAlertStart] = useState("");
  const [alertEnd, setAlertEnd] = useState("");
  const [alertRisk, setAlertRisk] = useState("all");
  const [exportingWeather, setExportingWeather] = useState(false);
  const [exportingPreds, setExportingPreds] = useState(false);
  const [exportingAlerts, setExportingAlerts] = useState(false);

  // ── Refresh ──
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // ── Queries ──
  const queryClient = useQueryClient();
  const {
    data: statsData,
    isLoading: statsLoading,
    dataUpdatedAt,
  } = useDatasetStats();

  const wxCountParams = useMemo(
    () => ({
      start_date: wxStart || undefined,
      end_date: wxEnd || undefined,
      source: wxSource !== "all" ? wxSource : undefined,
    }),
    [wxStart, wxEnd, wxSource],
  );
  const predCountParams = useMemo(
    () => ({
      start_date: predStart || undefined,
      end_date: predEnd || undefined,
      risk_level: predRisk !== "all" ? predRisk : undefined,
    }),
    [predStart, predEnd, predRisk],
  );
  const alertCountParams = useMemo(
    () => ({
      start_date: alertStart || undefined,
      end_date: alertEnd || undefined,
      risk_level: alertRisk !== "all" ? alertRisk : undefined,
    }),
    [alertStart, alertEnd, alertRisk],
  );

  const { data: wxCount, isLoading: wxCountLoading } =
    useWeatherCount(wxCountParams);
  const { data: predCount, isLoading: predCountLoading } =
    usePredictionsCount(predCountParams);
  const { data: alertCount, isLoading: alertCountLoading } =
    useAlertsCount(alertCountParams);

  // ── Derived stats ──
  const stats = statsData?.stats;
  const displayUpdatedAt =
    lastRefreshed ?? (dataUpdatedAt ? new Date(dataUpdatedAt) : null);

  // ── Handlers ──
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: datasetQueryKeys.all });
    setLastRefreshed(new Date());
    setIsRefreshing(false);
  }, [queryClient]);

  const handleFileSelect = useCallback((file: File) => {
    setFileError(null);
    setValidation(null);
    setUploadResult(null);
    setUploadProgress(null);

    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !["csv", "xlsx", "xls"].includes(ext)) {
      setFileError("Only CSV and Excel (.xlsx, .xls) files are accepted.");
      return;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setFileError(
        `File exceeds ${MAX_FILE_SIZE_MB}MB limit (${formatFileSize(file.size)}).`,
      );
      return;
    }
    setSelectedFile(file);
  }, []);

  const handleClear = useCallback(() => {
    setSelectedFile(null);
    setValidation(null);
    setUploadResult(null);
    setFileError(null);
    setUploadProgress(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  const handleValidate = useCallback(async () => {
    if (!selectedFile) return;
    setValidating(true);
    setValidation(null);
    setUploadResult(null);

    try {
      const result = await datasetApi.validateFile(selectedFile);
      setValidation(result);

      const valid = result.validation?.valid ?? result.data?.valid ?? false;
      const rows = result.validation?.total_rows ?? result.data?.records ?? 0;
      if (valid) {
        toast.success(`Validation passed: ${rows} records`);
      } else {
        const errCount =
          result.validation?.invalid_rows ?? result.data?.errors?.length ?? 0;
        toast.error(`Validation failed with ${errCount} error(s)`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Validation failed";
      toast.error(msg);
    } finally {
      setValidating(false);
    }
  }, [selectedFile]);

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;
    setUploading(true);
    setUploadResult(null);
    setUploadProgress("Uploading file...");

    try {
      const ext = selectedFile.name.split(".").pop()?.toLowerCase();
      setUploadProgress("Processing and ingesting data...");
      const result =
        ext === "csv"
          ? await datasetApi.uploadCsv(selectedFile, true)
          : await datasetApi.uploadExcel(selectedFile, true);

      setUploadResult(result);
      setUploadProgress(null);

      if (result.success) {
        const inserted =
          result.summary?.rows_inserted ?? result.data?.records_inserted ?? 0;
        toast.success(`Uploaded: ${inserted} records ingested`);
        // Refresh dataset stats after successful upload
        queryClient.invalidateQueries({ queryKey: datasetQueryKeys.all });
      } else {
        toast.error("Upload failed — see details below");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      toast.error(msg);
      setUploadProgress(null);
    } finally {
      setUploading(false);
    }
  }, [selectedFile, queryClient]);

  const handleDownloadTemplate = useCallback(async (fmt: "csv" | "info") => {
    try {
      if (fmt === "csv") {
        const blob = await datasetApi.downloadTemplateCsv();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "floodingnaque_upload_template.csv";
        a.click();
        URL.revokeObjectURL(url);
      } else {
        const blob = await datasetApi.downloadTemplateCsv();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "floodingnaque_upload_template.csv";
        a.click();
        URL.revokeObjectURL(url);
      }
      toast.success("Template downloaded");
    } catch {
      toast.error("Failed to download template");
    }
  }, []);

  // ── Export helpers ──

  function triggerDownload(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  const handleExportWeather = useCallback(async () => {
    setExportingWeather(true);
    try {
      const blob = await datasetApi.exportWeather({
        start_date: wxStart || undefined,
        end_date: wxEnd || undefined,
        source: wxSource !== "all" ? wxSource : undefined,
      });
      triggerDownload(
        blob,
        `weather_data_${format(new Date(), "yyyyMMdd_HHmmss")}.csv`,
      );
      toast.success("Weather data exported");
    } catch {
      toast.error("Failed to export weather data");
    } finally {
      setExportingWeather(false);
    }
  }, [wxStart, wxEnd, wxSource]);

  const handleExportPredictions = useCallback(async () => {
    setExportingPreds(true);
    try {
      const blob = await datasetApi.exportPredictions({
        start_date: predStart || undefined,
        end_date: predEnd || undefined,
        risk_level: predRisk !== "all" ? predRisk : undefined,
      });
      triggerDownload(
        blob,
        `predictions_${format(new Date(), "yyyyMMdd_HHmmss")}.csv`,
      );
      toast.success("Predictions exported");
    } catch {
      toast.error("Failed to export predictions");
    } finally {
      setExportingPreds(false);
    }
  }, [predStart, predEnd, predRisk]);

  const handleExportAlerts = useCallback(async () => {
    setExportingAlerts(true);
    try {
      const blob = await datasetApi.exportAlerts({
        start_date: alertStart || undefined,
        end_date: alertEnd || undefined,
        risk_level: alertRisk !== "all" ? alertRisk : undefined,
      });
      triggerDownload(
        blob,
        `alerts_${format(new Date(), "yyyyMMdd_HHmmss")}.csv`,
      );
      toast.success("Alerts exported");
    } catch {
      toast.error("Failed to export alerts");
    } finally {
      setExportingAlerts(false);
    }
  }, [alertStart, alertEnd, alertRisk]);

  // ── Validation display helpers ──
  const validationValid =
    validation?.validation?.valid ?? validation?.data?.valid ?? false;
  const validationRows =
    validation?.validation?.total_rows ?? validation?.data?.records ?? 0;
  const validationErrors =
    validation?.validation?.errors ?? validation?.data?.errors ?? [];
  const validationWarnings = validation?.data?.warnings ?? [];
  const validationSample = validation?.data?.sample ?? [];

  // ── Refs for animations ──
  const statsRef = useRef<HTMLDivElement>(null);
  const statsInView = useInView(statsRef, { once: true, amount: 0.1 });
  const uploadRef = useRef<HTMLDivElement>(null);
  const uploadInView = useInView(uploadRef, { once: true, amount: 0.1 });
  const exportRef = useRef<HTMLDivElement>(null);
  const exportInView = useInView(exportRef, { once: true, amount: 0.1 });

  // ── File type badge ──
  const fileExt = selectedFile?.name.split(".").pop()?.toLowerCase();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <div className="flex items-start justify-between">
          <PageHeader
            icon={Database}
            title="Dataset Management"
            subtitle="Upload, validate, and export weather observation data"
          />
          <div className="flex items-center gap-3 pt-1">
            {displayUpdatedAt && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Updated{" "}
                {formatDistanceToNow(displayUpdatedAt, { addSuffix: true })}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={cn("h-4 w-4 mr-1.5", isRefreshing && "animate-spin")}
              />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* ── Dataset Overview Stats ── */}
      <section className="py-6 bg-background">
        <div className="w-full px-6" ref={statsRef}>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={statsInView ? "show" : undefined}
            className="grid gap-4 grid-cols-2 lg:grid-cols-5"
          >
            {[
              {
                label: "Total Records",
                value: stats?.total_records?.toLocaleString() ?? "—",
                icon: Database,
                health: "neutral" as AccentLevel,
              },
              {
                label: "Date Coverage",
                value: stats?.date_range?.earliest
                  ? `${format(new Date(stats.date_range.earliest), "MMM yyyy")} – ${stats.date_range.latest ? format(new Date(stats.date_range.latest), "MMM yyyy") : "now"}`
                  : "—",
                icon: Calendar,
                health: "neutral" as AccentLevel,
              },
              {
                label: "Data Sources",
                value: stats?.sources?.length ?? "—",
                icon: Server,
                health: "neutral" as AccentLevel,
                description: stats?.sources?.join(", "),
              },
              {
                label: "Last Ingestion",
                value: stats?.last_ingestion
                  ? formatDistanceToNow(new Date(stats.last_ingestion), {
                      addSuffix: true,
                    })
                  : "—",
                icon: Upload,
                health: "good" as AccentLevel,
              },
              {
                label: "Records This Month",
                value: stats?.records_this_month?.toLocaleString() ?? "—",
                icon: CloudRain,
                health: "warn" as AccentLevel,
              },
            ].map(({ label, value, icon, health, description }) => (
              <motion.div key={label} variants={fadeUp}>
                <StatCard
                  icon={icon}
                  label={label}
                  value={value}
                  isLoading={statsLoading}
                  health={health}
                  description={description}
                />
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Upload Section ── */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={uploadRef}>
          <SectionHeading
            label="Import"
            title="Upload Weather Data"
            subtitle="Upload CSV or Excel files for validation and ingestion into the weather database"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={uploadInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <div className="pt-6 px-6 pb-6 space-y-5">
                  {/* Template downloads */}
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDownloadTemplate("csv")}
                    >
                      <Download className="h-4 w-4 mr-1.5" />
                      Download CSV Template
                    </Button>
                  </div>

                  {/* Drop Zone (only shown when no file selected) */}
                  {!selectedFile && (
                    <FileDropZone
                      onFileSelect={handleFileSelect}
                      disabled={uploading || validating}
                    />
                  )}

                  {/* File Error */}
                  {fileError && (
                    <div className="rounded-lg border border-risk-critical/20 bg-risk-critical/5 p-3 flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-risk-critical shrink-0" />
                      <p className="text-sm text-risk-critical">{fileError}</p>
                    </div>
                  )}

                  {/* Selected File Preview */}
                  {selectedFile && (
                    <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {fileExt === "csv" ? (
                            <FileText className="h-8 w-8 text-primary/60" />
                          ) : (
                            <FileSpreadsheet className="h-8 w-8 text-risk-safe/60" />
                          )}
                          <div>
                            <p className="font-medium text-sm">
                              {selectedFile.name}
                            </p>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-xs text-muted-foreground">
                                {formatFileSize(selectedFile.size)}
                              </span>
                              <Badge
                                variant="outline"
                                className="text-[10px] uppercase"
                              >
                                {fileExt}
                              </Badge>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleValidate}
                            disabled={validating || uploading}
                          >
                            {validating ? (
                              <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                            ) : (
                              <Eye className="h-4 w-4 mr-1.5" />
                            )}
                            Validate
                          </Button>
                          <Button
                            size="sm"
                            onClick={handleUpload}
                            disabled={
                              uploading ||
                              validating ||
                              (validation != null && !validationValid)
                            }
                          >
                            {uploading ? (
                              <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                            ) : (
                              <Upload className="h-4 w-4 mr-1.5" />
                            )}
                            Ingest
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={handleClear}
                            disabled={uploading || validating}
                            aria-label="Clear selected file"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      {/* Upload progress */}
                      {uploadProgress && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {uploadProgress}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Validation Results */}
                  {validation && (
                    <>
                      <Separator />
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          {validationValid ? (
                            <Badge
                              className="bg-risk-safe/10 text-risk-safe border-risk-safe/30"
                              variant="outline"
                            >
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Valid
                            </Badge>
                          ) : (
                            <Badge
                              className="bg-risk-critical/10 text-risk-critical border-risk-critical/30"
                              variant="outline"
                            >
                              <AlertTriangle className="h-3 w-3 mr-1" />
                              Invalid
                            </Badge>
                          )}
                          <span className="text-sm text-muted-foreground">
                            {validationRows} records found
                          </span>
                          {validation.validation && (
                            <span className="text-xs text-muted-foreground">
                              ({validation.validation.valid_rows} valid,{" "}
                              {validation.validation.invalid_rows} invalid)
                            </span>
                          )}
                        </div>

                        {/* Passed checks */}
                        {validationValid && (
                          <div className="rounded-lg border border-risk-safe/20 bg-risk-safe/5 p-3 flex items-start gap-2">
                            <CheckCircle className="h-4 w-4 text-risk-safe mt-0.5 shrink-0" />
                            <div>
                              <p className="text-sm font-medium text-risk-safe">
                                All checks passed
                              </p>
                              <p className="text-xs text-muted-foreground">
                                Required columns present, data types valid,
                                values within thresholds.
                              </p>
                            </div>
                          </div>
                        )}

                        {/* Errors */}
                        {validationErrors.length > 0 && (
                          <div className="rounded-lg border border-risk-critical/20 bg-risk-critical/5 p-3 space-y-1">
                            <p className="text-sm font-medium text-risk-critical flex items-center gap-1">
                              <XCircle className="h-3.5 w-3.5" />
                              {validationErrors.length} error(s) — must be
                              resolved before ingestion
                            </p>
                            <ul className="text-xs text-risk-critical space-y-0.5 max-h-40 overflow-y-auto">
                              {validationErrors.map((e, i) => (
                                <li key={i}>• {e}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Warnings */}
                        {validationWarnings.length > 0 && (
                          <div className="rounded-lg border border-risk-alert/20 bg-risk-alert/5 p-3 space-y-1">
                            <p className="text-sm font-medium text-risk-alert flex items-center gap-1">
                              <AlertTriangle className="h-3.5 w-3.5" />
                              {validationWarnings.length} warning(s) —
                              non-blocking
                            </p>
                            <ul className="text-xs text-risk-alert space-y-0.5 max-h-40 overflow-y-auto">
                              {validationWarnings.map((w, i) => (
                                <li key={i}>• {w}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Preview Table */}
                        {validationSample.length > 0 && (
                          <div>
                            <p className="text-sm font-medium mb-2">
                              Preview (first {validationSample.length} rows)
                            </p>
                            <div className="overflow-x-auto rounded border">
                              <Table>
                                <TableHeader>
                                  <TableRow>
                                    {Object.keys(validationSample[0]!).map(
                                      (col) => (
                                        <TableHead
                                          key={col}
                                          className="text-xs whitespace-nowrap"
                                        >
                                          {col
                                            .replace(/_/g, " ")
                                            .replace(/\b\w/g, (c) =>
                                              c.toUpperCase(),
                                            )}
                                        </TableHead>
                                      ),
                                    )}
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {validationSample.map((row, i) => (
                                    <TableRow key={i}>
                                      {Object.values(row).map((val, j) => (
                                        <TableCell key={j} className="text-xs">
                                          {String(val ?? "")}
                                        </TableCell>
                                      ))}
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </div>
                        )}
                      </div>
                    </>
                  )}

                  {/* Upload Result */}
                  {uploadResult && (
                    <>
                      <Separator />
                      <div
                        className={cn(
                          "rounded-lg border p-4 space-y-2",
                          uploadResult.success
                            ? "border-risk-safe/20 bg-risk-safe/5"
                            : "border-risk-critical/20 bg-risk-critical/5",
                        )}
                      >
                        <div className="flex items-center gap-2">
                          {uploadResult.success ? (
                            <CheckCircle className="h-5 w-5 text-risk-safe" />
                          ) : (
                            <AlertTriangle className="h-5 w-5 text-risk-critical" />
                          )}
                          <p className="font-medium text-sm">
                            {uploadResult.success
                              ? "Ingestion Complete"
                              : "Ingestion Failed"}
                          </p>
                        </div>

                        {/* Summary table */}
                        {(uploadResult.summary || uploadResult.data) && (
                          <div className="grid grid-cols-3 gap-3 mt-2">
                            <div className="rounded border p-2 text-center">
                              <p className="text-lg font-bold">
                                {uploadResult.summary?.total_rows_processed ??
                                  uploadResult.data?.records_processed ??
                                  0}
                              </p>
                              <p className="text-[10px] text-muted-foreground">
                                Total Processed
                              </p>
                            </div>
                            <div className="rounded border p-2 text-center">
                              <p className="text-lg font-bold text-risk-safe">
                                {uploadResult.summary?.rows_inserted ??
                                  uploadResult.data?.records_inserted ??
                                  0}
                              </p>
                              <p className="text-[10px] text-muted-foreground">
                                Ingested
                              </p>
                            </div>
                            <div className="rounded border p-2 text-center">
                              <p className="text-lg font-bold text-risk-alert">
                                {uploadResult.summary?.rows_skipped ?? 0}
                              </p>
                              <p className="text-[10px] text-muted-foreground">
                                Skipped
                              </p>
                            </div>
                          </div>
                        )}

                        {/* Errors */}
                        {(
                          uploadResult.summary?.errors ??
                          uploadResult.data?.errors ??
                          []
                        ).length > 0 && (
                          <ul className="text-xs text-risk-critical space-y-0.5 mt-2 max-h-32 overflow-y-auto">
                            {(
                              uploadResult.summary?.errors ??
                              uploadResult.data?.errors ??
                              []
                            )
                              .slice(0, 20)
                              .map((e, i) => (
                                <li key={i}>• {e}</li>
                              ))}
                          </ul>
                        )}

                        <p className="text-[10px] text-muted-foreground mt-1">
                          Ingested at{" "}
                          {format(new Date(), "yyyy-MM-dd HH:mm:ss")}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Data Export Section ── */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={exportRef}>
          <SectionHeading
            label="Export"
            title="Data Export"
            subtitle="Download datasets with date range and source filters"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={exportInView ? "show" : undefined}
          >
            <motion.div
              variants={fadeUp}
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
            >
              {/* Weather */}
              <ExportCard
                title="Weather Data"
                icon={CloudRain}
                description="Historical weather observations"
                count={wxCount?.count}
                countLoading={wxCountLoading}
                exporting={exportingWeather}
                onExport={handleExportWeather}
                filterContent={
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <Input
                        type="date"
                        value={wxStart}
                        onChange={(e) => setWxStart(e.target.value)}
                        className="h-8 text-xs"
                        aria-label="Weather start date"
                      />
                      <Input
                        type="date"
                        value={wxEnd}
                        onChange={(e) => setWxEnd(e.target.value)}
                        className="h-8 text-xs"
                        aria-label="Weather end date"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <DatePresets
                        onSelect={(s, e) => {
                          setWxStart(s);
                          setWxEnd(e);
                        }}
                      />
                    </div>
                    <Select value={wxSource} onValueChange={setWxSource}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="All Sources" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Sources</SelectItem>
                        {(stats?.sources ?? []).map((s) => (
                          <SelectItem key={s} value={s}>
                            {s}
                          </SelectItem>
                        ))}
                        <SelectItem value="PAGASA">PAGASA</SelectItem>
                        <SelectItem value="OpenWeatherMap">
                          OpenWeatherMap
                        </SelectItem>
                        <SelectItem value="Meteostat">Meteostat</SelectItem>
                        <SelectItem value="CSV_Upload">
                          Manual Upload
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                }
              />

              {/* Predictions */}
              <ExportCard
                title="Predictions"
                icon={FileText}
                description="Historical flood prediction records"
                count={predCount?.count}
                countLoading={predCountLoading}
                exporting={exportingPreds}
                onExport={handleExportPredictions}
                filterContent={
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <Input
                        type="date"
                        value={predStart}
                        onChange={(e) => setPredStart(e.target.value)}
                        className="h-8 text-xs"
                        aria-label="Predictions start date"
                      />
                      <Input
                        type="date"
                        value={predEnd}
                        onChange={(e) => setPredEnd(e.target.value)}
                        className="h-8 text-xs"
                        aria-label="Predictions end date"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <DatePresets
                        onSelect={(s, e) => {
                          setPredStart(s);
                          setPredEnd(e);
                        }}
                      />
                    </div>
                    <Select value={predRisk} onValueChange={setPredRisk}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="All Risk Levels" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Risk Levels</SelectItem>
                        <SelectItem value="0">Safe (0)</SelectItem>
                        <SelectItem value="1">Alert (1)</SelectItem>
                        <SelectItem value="2">Critical (2)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                }
              />

              {/* Alerts */}
              <ExportCard
                title="Alerts"
                icon={AlertTriangle}
                description="Alert delivery & incident history"
                count={alertCount?.count}
                countLoading={alertCountLoading}
                exporting={exportingAlerts}
                onExport={handleExportAlerts}
                filterContent={
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <Input
                        type="date"
                        value={alertStart}
                        onChange={(e) => setAlertStart(e.target.value)}
                        className="h-8 text-xs"
                        aria-label="Alerts start date"
                      />
                      <Input
                        type="date"
                        value={alertEnd}
                        onChange={(e) => setAlertEnd(e.target.value)}
                        className="h-8 text-xs"
                        aria-label="Alerts end date"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <DatePresets
                        onSelect={(s, e) => {
                          setAlertStart(s);
                          setAlertEnd(e);
                        }}
                      />
                    </div>
                    <Select value={alertRisk} onValueChange={setAlertRisk}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="All Risk Levels" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Risk Levels</SelectItem>
                        <SelectItem value="0">Safe (0)</SelectItem>
                        <SelectItem value="1">Alert (1)</SelectItem>
                        <SelectItem value="2">Critical (2)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                }
              />
            </motion.div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
