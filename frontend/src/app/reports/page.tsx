/**
 * Reports Page — Landing-page-inspired overhaul
 *
 * Page for generating and exporting reports in various formats.
 * Provides access to prediction, alert, and weather data exports.
 */

import { motion, useInView } from "framer-motion";
import {
  Bell,
  Brain,
  CheckCircle2,
  CloudRain,
  Download,
  FileText,
  HelpCircle,
  Lock,
  MapPin,
  Shield,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { fadeUp, staggerContainer } from "@/lib/motion";

import { Badge } from "@/components/ui/badge";
import {
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { ReportGenerator } from "@/features/reports/components/ReportGenerator";
import type { ReportType } from "@/features/reports/services/reportsApi";
import { cn } from "@/lib/utils";

import type { LucideIcon } from "lucide-react";

interface ReportCard {
  icon: LucideIcon;
  title: string;
  description: string;
  sheets: string[];
  formats: { label: string; available: boolean }[];
  color: string;
  /** Maps to ReportType. null = coming soon (disabled). */
  reportType: ReportType | null;
}

const DISASTER_REPORTS: ReportCard[] = [
  {
    icon: CloudRain,
    title: "Monthly Flood Report",
    description:
      "Comprehensive monthly summary of flood predictions, recorded rainfall, and risk level distribution across all 16 barangays.",
    sheets: ["Predictions", "Daily Rainfall", "Risk Distribution"],
    formats: [
      { label: "PDF", available: true },
      { label: "CSV", available: true },
    ],
    color: "from-blue-500/60 via-blue-600 to-blue-500/60",
    reportType: "monthly-flood",
  },
  {
    icon: MapPin,
    title: "Barangay Risk Assessment",
    description:
      "Per-barangay risk profile including zone classification, historical flood frequency, population exposure, and vulnerability index.",
    sheets: ["Risk Profiles", "Flood History", "Population Data"],
    formats: [
      { label: "PDF", available: true },
      { label: "CSV", available: true },
    ],
    color: "from-risk-alert/60 via-risk-alert to-risk-alert/60",
    reportType: "barangay-risk",
  },
  {
    icon: Bell,
    title: "Flood Incident Log",
    description:
      "Alert history with triggered timestamps, affected areas, severity levels, acknowledgment status, and response times.",
    sheets: ["Alerts", "Severity Timeline", "Response Audit"],
    formats: [
      { label: "PDF", available: true },
      { label: "CSV", available: true },
    ],
    color: "from-risk-critical/60 via-risk-critical to-risk-critical/60",
    reportType: "incident-log",
  },
  {
    icon: Brain,
    title: "ML Model Performance",
    description:
      "Model accuracy, precision, recall, F1 score, and progressive training history from v1 baseline through current production version.",
    sheets: ["Metrics Summary", "Version Comparison", "Feature Importance"],
    formats: [
      { label: "PDF", available: false },
      { label: "CSV", available: false },
    ],
    color: "from-purple-500/60 via-purple-600 to-purple-500/60",
    reportType: null,
  },
  {
    icon: Shield,
    title: "Disaster Preparedness",
    description:
      "Evacuation route readiness, emergency resource inventory, shelter capacity, and communication system status for Parañaque City.",
    sheets: ["Evacuations", "Resources", "Shelter Capacity"],
    formats: [
      { label: "PDF", available: false },
      { label: "CSV", available: false },
    ],
    color: "from-risk-safe/60 via-risk-safe to-risk-safe/60",
    reportType: null,
  },
];

/**
 * ReportsPage - Main page for report generation and export
 */
export default function ReportsPage() {
  const mainRef = useRef<HTMLDivElement>(null);
  const mainInView = useInView(mainRef, { once: true, amount: 0.1 });
  const cardsRef = useRef<HTMLDivElement>(null);
  const cardsInView = useInView(cardsRef, { once: true, amount: 0.1 });
  const generatorRef = useRef<HTMLDivElement>(null);

  const [preselectedType, setPreselectedType] = useState<ReportType | null>(
    null,
  );

  const handleCardClick = useCallback((type: ReportType | null) => {
    if (!type) return;
    setPreselectedType(type);
    setTimeout(() => {
      generatorRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 100);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <PageHeader
          icon={FileText}
          title="Reports & Export"
          subtitle="Generate and download reports for analysis and record keeping"
        />
      </div>

      {/* Disaster Report Cards */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={cardsRef}>
          <SectionHeading
            label="Reports"
            title="Disaster Report Catalog"
            subtitle="Available report types for Parañaque City flood monitoring"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={cardsInView ? "show" : undefined}
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          >
            {DISASTER_REPORTS.map((report) => {
              const Icon = report.icon;
              const isAvailable = report.reportType !== null;
              const isSelected = preselectedType === report.reportType;

              return (
                <motion.div key={report.title} variants={fadeUp}>
                  <GlassCard
                    className={cn(
                      "overflow-hidden transition-all duration-300 h-full flex flex-col",
                      isAvailable
                        ? "cursor-pointer hover:shadow-lg hover:ring-1 hover:ring-primary/30"
                        : "cursor-not-allowed opacity-60",
                      isSelected && "ring-2 ring-primary shadow-lg",
                    )}
                    onClick={() => handleCardClick(report.reportType)}
                    title={
                      isAvailable
                        ? "Click to generate this report"
                        : "This report type is under development"
                    }
                  >
                    <div
                      className={cn("h-1 w-full bg-linear-to-r", report.color)}
                    />
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <div
                          className={cn(
                            "flex h-8 w-8 items-center justify-center rounded-xl ring-1",
                            isAvailable
                              ? "bg-primary/10 ring-primary/20"
                              : "bg-muted ring-muted-foreground/20",
                          )}
                        >
                          <Icon
                            className={cn(
                              "h-4 w-4",
                              isAvailable
                                ? "text-primary"
                                : "text-muted-foreground",
                            )}
                          />
                        </div>
                        {report.title}
                        {isAvailable ? (
                          <Badge
                            variant="outline"
                            className="ml-auto text-[10px] text-risk-safe border-risk-safe/30"
                          >
                            <CheckCircle2 className="h-3 w-3 mr-0.5" />
                            Available
                          </Badge>
                        ) : (
                          <Badge
                            variant="secondary"
                            className="ml-auto text-[10px] gap-0.5"
                          >
                            <Lock className="h-3 w-3" />
                            Coming Soon
                          </Badge>
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 flex flex-col gap-3">
                      <CardDescription className="text-xs">
                        {report.description}
                      </CardDescription>
                      <div className="flex flex-wrap gap-1.5">
                        {report.sheets.map((sheet) => (
                          <Badge
                            key={sheet}
                            variant="outline"
                            className={cn(
                              "text-[10px] px-1.5 py-0",
                              !isAvailable && "opacity-50",
                            )}
                          >
                            {sheet}
                          </Badge>
                        ))}
                      </div>
                      <div className="mt-auto flex gap-2">
                        {report.formats.map((fmt) => (
                          <Badge
                            key={fmt.label}
                            variant={fmt.available ? "default" : "secondary"}
                            className={cn(
                              "text-[10px]",
                              !fmt.available && "opacity-50",
                            )}
                          >
                            {fmt.label}
                            {!fmt.available && " — soon"}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  </GlassCard>
                </motion.div>
              );
            })}

            {/* Privacy Notice */}
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden border-muted-foreground/20 bg-muted/10 h-full">
                <div className="h-1 w-full bg-linear-to-r from-muted-foreground/20 via-muted-foreground/40 to-muted-foreground/20" />
                <CardContent className="pt-5">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    <strong>Privacy Notice:</strong> Exported reports may
                    contain sensitive location and timing data. Please handle
                    exported files responsibly and in accordance with data
                    protection guidelines.
                  </p>
                </CardContent>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Report Generator */}
      <section className="py-10 bg-background" ref={generatorRef}>
        <div className="w-full px-6">
          <div className="grid gap-8 lg:grid-cols-[1fr_350px]">
            <div className="space-y-6" ref={mainRef}>
              <SectionHeading
                label="Generate"
                title="Export Report"
                subtitle="Select report type, format, and date range to generate downloadable reports."
              />

              <motion.div
                variants={staggerContainer}
                initial="hidden"
                animate={mainInView ? "show" : undefined}
              >
                <motion.div variants={fadeUp}>
                  <ReportGenerator preselectedType={preselectedType} />
                </motion.div>
              </motion.div>
            </div>

            {/* Guide Sidebar */}
            <div>
              <SectionHeading label="Guide" title="How It Works" />

              <motion.div
                variants={staggerContainer}
                initial="hidden"
                animate={mainInView ? "show" : undefined}
                className="space-y-3"
              >
                <motion.div variants={fadeUp}>
                  <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                    <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                    <div className="p-5 pb-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                          <HelpCircle className="h-4 w-4 text-primary" />
                        </div>
                        <h3 className="text-sm font-semibold">Steps</h3>
                      </div>
                    </div>
                    <div className="px-5 pb-5">
                      <ol className="list-inside list-decimal space-y-2 text-xs text-muted-foreground">
                        <li>
                          Select a report type (or click a catalog card above)
                        </li>
                        <li>Choose export format (PDF or CSV)</li>
                        <li>Set a date range or use quick presets</li>
                        <li>Click &quot;Generate &amp; Download&quot;</li>
                      </ol>
                    </div>
                  </GlassCard>
                </motion.div>

                <motion.div variants={fadeUp}>
                  <GlassCard className="overflow-hidden">
                    <div className="h-0.5 w-full bg-linear-to-r from-primary/40 via-primary/60 to-primary/40" />
                    <CardContent className="pt-4 space-y-3">
                      <p className="text-xs font-medium">Format Comparison</p>
                      <div className="space-y-2">
                        <div className="rounded-lg border p-2.5">
                          <div className="flex items-center gap-2 text-xs font-medium">
                            <FileText className="h-3.5 w-3.5" />
                            PDF
                          </div>
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            Best for printing and formal documentation. Includes
                            cover page, table of contents, and privacy notice.
                          </p>
                        </div>
                        <div className="rounded-lg border p-2.5">
                          <div className="flex items-center gap-2 text-xs font-medium">
                            <Download className="h-3.5 w-3.5" />
                            CSV
                          </div>
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            Best for data analysis in Excel or Sheets. Includes
                            metadata header row.
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </GlassCard>
                </motion.div>
              </motion.div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
