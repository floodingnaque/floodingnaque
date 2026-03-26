/**
 * ReportGenerator Component
 *
 * Form component for configuring and generating reports in PDF or CSV format.
 * Supports 5 report types (3 available, 2 coming soon), date range selection
 * with quick presets, and success/error feedback states.
 */

import { zodResolver } from "@hookform/resolvers/zod";
import { format, subDays } from "date-fns";
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  FileText,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { useCallback, useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useReportExport } from "../hooks/useReports";
import type { ReportType } from "../services/reportsApi";

/**
 * Report type options - matches the Disaster Report Catalog cards.
 */
const REPORT_TYPES: {
  value: ReportType;
  label: string;
  description: string;
  available: boolean;
}[] = [
  {
    value: "monthly-flood",
    label: "Monthly Flood Report",
    description: "Predictions, daily rainfall, and risk distribution",
    available: true,
  },
  {
    value: "barangay-risk",
    label: "Barangay Risk Assessment",
    description: "Risk profiles, flood history, and weather observations",
    available: true,
  },
  {
    value: "incident-log",
    label: "Flood Incident Log",
    description: "Alert history, severity, and response audit",
    available: true,
  },
  {
    value: "ml-performance",
    label: "ML Model Performance",
    description: "Accuracy, precision, recall, F1, and feature importance",
    available: true,
  },
  {
    value: "disaster-preparedness",
    label: "Disaster Preparedness",
    description: "Evacuation center readiness and shelter capacity",
    available: true,
  },
];

/**
 * Export format options
 */
const EXPORT_FORMATS: {
  value: "pdf" | "csv";
  label: string;
  icon: typeof FileText;
}[] = [
  { value: "pdf", label: "PDF Document", icon: FileText },
  { value: "csv", label: "CSV Spreadsheet", icon: FileSpreadsheet },
];

/**
 * Form validation schema
 */
const reportFormSchema = z
  .object({
    reportType: z.enum([
      "monthly-flood",
      "barangay-risk",
      "incident-log",
      "predictions",
      "weather",
      "alerts",
      "ml-performance",
      "disaster-preparedness",
    ]),
    format: z.enum(["pdf", "csv"]),
    startDate: z.string().min(1, "Start date is required"),
    endDate: z.string().min(1, "End date is required"),
  })
  .refine(
    (data) => {
      return new Date(data.startDate) <= new Date(data.endDate);
    },
    {
      message: "Start date must be before or equal to end date",
      path: ["endDate"],
    },
  );

type ReportFormValues = z.infer<typeof reportFormSchema>;

export interface ReportGeneratorProps {
  /** Pre-selected report type (from clicking a catalog card) */
  preselectedType?: ReportType | null;
  /** Additional CSS classes */
  className?: string;
}

/**
 * ReportGenerator - Form for generating and downloading reports
 */
export function ReportGenerator({
  preselectedType,
  className,
}: ReportGeneratorProps) {
  const { exportReport, isExporting, isSuccess, isError, error, reset } =
    useReportExport();

  const defaultStart = format(subDays(new Date(), 30), "yyyy-MM-dd");
  const defaultEnd = format(new Date(), "yyyy-MM-dd");

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = useForm<ReportFormValues>({
    resolver: zodResolver(reportFormSchema),
    defaultValues: {
      reportType: "monthly-flood",
      format: "pdf",
      startDate: defaultStart,
      endDate: defaultEnd,
    },
  });

  const watchFormat = useWatch({ control, name: "format" });
  const watchReportType = useWatch({ control, name: "reportType" });

  // Sync pre-selected type from catalog card click
  useEffect(() => {
    if (preselectedType) {
      setValue("reportType", preselectedType);
      reset(); // Clear any previous success/error state
    }
  }, [preselectedType, setValue, reset]);

  // Handle form submission
  const onSubmit = useCallback(
    (data: ReportFormValues) => {
      exportReport(
        {
          report_type: data.reportType as ReportType,
          start_date: data.startDate,
          end_date: data.endDate,
        },
        data.format,
      );
    },
    [exportReport],
  );

  // Set quick date range
  const setQuickRange = useCallback(
    (days: number) => {
      const endDate = new Date();
      const startDate = subDays(endDate, days);
      setValue("startDate", format(startDate, "yyyy-MM-dd"));
      setValue("endDate", format(endDate, "yyyy-MM-dd"));
      reset(); // Clear previous feedback
    },
    [setValue, reset],
  );

  return (
    <GlassCard className={cn("w-full overflow-hidden", className)}>
      {/* Primary gradient accent bar */}
      <div className="h-1.5 w-full bg-linear-to-r from-primary/80 via-primary to-primary/80" />

      <CardHeader className="space-y-2">
        <CardTitle className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          Generate Report
        </CardTitle>
        <CardDescription>
          Configure and export reports in PDF or CSV format
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Report Type Selection */}
          <div className="space-y-2">
            <Label htmlFor="reportType">Report Type</Label>
            <Select
              value={watchReportType}
              onValueChange={(value: string) => {
                setValue("reportType", value as ReportType);
                reset();
              }}
            >
              <SelectTrigger id="reportType">
                <SelectValue placeholder="Select report type" />
              </SelectTrigger>
              <SelectContent>
                {REPORT_TYPES.map((type) => (
                  <SelectItem
                    key={type.value}
                    value={type.value}
                    disabled={!type.available}
                  >
                    <div className="flex flex-col">
                      <span>{type.label}</span>
                      <span className="text-xs text-muted-foreground">
                        {type.description}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Export Format Selection */}
          <div className="space-y-2">
            <Label htmlFor="format">Export Format</Label>
            <Select
              value={watchFormat}
              onValueChange={(value: "pdf" | "csv") => {
                setValue("format", value);
                reset();
              }}
            >
              <SelectTrigger id="format">
                <SelectValue placeholder="Select format" />
              </SelectTrigger>
              <SelectContent>
                {EXPORT_FORMATS.map((fmt) => (
                  <SelectItem key={fmt.value} value={fmt.value}>
                    <div className="flex items-center gap-2">
                      <fmt.icon className="h-4 w-4" />
                      <span>{fmt.label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Date Range */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Date Range</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setQuickRange(7)}
                >
                  7 days
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setQuickRange(30)}
                >
                  30 days
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setQuickRange(90)}
                >
                  90 days
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label
                  htmlFor="startDate"
                  className="text-xs text-muted-foreground"
                >
                  Start Date
                </Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="startDate"
                    type="date"
                    className="pl-10"
                    {...register("startDate")}
                  />
                </div>
                {errors.startDate && (
                  <p className="text-xs text-risk-critical mt-1">
                    {errors.startDate.message}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <Label
                  htmlFor="endDate"
                  className="text-xs text-muted-foreground"
                >
                  End Date
                </Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="endDate"
                    type="date"
                    className="pl-10"
                    {...register("endDate")}
                  />
                </div>
                {errors.endDate && (
                  <div className="mt-1 flex items-center gap-2 rounded-lg bg-linear-to-r from-risk-critical/10 to-risk-critical/10 px-3 py-1.5 ring-1 ring-risk-critical/20">
                    <p className="text-xs font-medium text-risk-critical">
                      {errors.endDate.message}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Generate Button */}
          <Button
            type="submit"
            className="w-full bg-linear-to-r from-primary to-primary/90 text-white shadow-lg shadow-primary/25 transition-all duration-300 hover:from-primary/90 hover:to-primary hover:shadow-primary/40 hover:scale-[1.02] active:scale-[0.98]"
            disabled={isExporting}
          >
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating Report...
              </>
            ) : (
              <>
                <div className="mr-2 flex h-6 w-6 items-center justify-center rounded-lg bg-white/20">
                  <Download className="h-3.5 w-3.5" />
                </div>
                Generate & Download
              </>
            )}
          </Button>

          {/* Success confirmation */}
          {isSuccess && (
            <div className="flex items-center gap-3 rounded-lg border border-risk-safe/30 bg-risk-safe/5 p-3">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-risk-safe" />
              <div className="flex-1">
                <p className="text-sm font-medium text-risk-safe">
                  Report Generated Successfully
                </p>
                <p className="text-xs text-muted-foreground">
                  Your download should start automatically.
                </p>
              </div>
            </div>
          )}

          {/* Error state with retry */}
          {isError && (
            <div className="flex items-center gap-3 rounded-lg border border-risk-critical/30 bg-risk-critical/5 p-3">
              <AlertTriangle className="h-5 w-5 shrink-0 text-risk-critical" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-risk-critical">
                  Generation Failed
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {error?.message || "An unexpected error occurred."}
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="shrink-0"
                onClick={() => handleSubmit(onSubmit)()}
              >
                <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                Retry
              </Button>
            </div>
          )}
        </form>
      </CardContent>
    </GlassCard>
  );
}

export default ReportGenerator;
