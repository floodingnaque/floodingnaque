/**
 * Reports Page - Accessible, plain-language report generation.
 *
 * Provides a catalog of downloadable flood monitoring reports and
 * a form to configure, generate, and export them in PDF or CSV.
 *
 * Accessibility:
 * - Semantic regions (main, nav, sections) with ARIA landmarks
 * - Report cards are keyboard-navigable buttons with role="option"
 * - Visual hierarchy via h1 → h2 → h3 heading levels
 * - Sufficient contrast ratios (WCAG AA)
 * - Skip-to-generator keyboard shortcut (anchor link)
 * - Contextual helper text + tooltips for first-time users
 */

import { motion, useInView } from "framer-motion";
import {
  ArrowDown,
  Bell,
  Brain,
  CheckCircle2,
  CloudRain,
  Download,
  FileText,
  HelpCircle,
  Info,
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
  /** Plain-language summary for general audiences. */
  description: string;
  /** Tooltip or detail hint shown on hover/focus for extra clarity. */
  hint: string;
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
      "A month-by-month overview of flood predictions, rainfall amounts, and which barangays were at risk.",
    hint: "Includes daily rainfall data, predicted risk levels, and a distribution chart for all 16 barangays.",
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
      "A detailed look at each barangay's flood risk - how often it floods, how many residents are affected, and its risk classification.",
    hint: "Shows risk profiles, historical flood frequency, population exposure, and vulnerability scores per barangay.",
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
      "A timeline of every flood alert - when it was triggered, which areas were affected, and how quickly it was handled.",
    hint: "Contains triggered timestamps, severity levels, acknowledgment status, and response time metrics.",
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
      "How well the flood prediction model is performing - its accuracy, how it has improved over time, and which factors matter most.",
    hint: "Reports accuracy, precision, recall, F1 score, progressive training history (v1–v6), and feature importance rankings.",
    sheets: ["Metrics Summary", "Version Comparison", "Feature Importance"],
    formats: [
      { label: "PDF", available: true },
      { label: "CSV", available: true },
    ],
    color: "from-purple-500/60 via-purple-600 to-purple-500/60",
    reportType: "ml-performance",
  },
  {
    icon: Shield,
    title: "Disaster Preparedness",
    description:
      "Are evacuation centers ready? This report covers shelter capacity, emergency resources, and communication system status.",
    hint: "Includes evacuation route readiness, resource inventory, current shelter occupancy, and comms infrastructure status.",
    sheets: ["Evacuations", "Resources", "Shelter Capacity"],
    formats: [
      { label: "PDF", available: true },
      { label: "CSV", available: true },
    ],
    color: "from-risk-safe/60 via-risk-safe to-risk-safe/60",
    reportType: "disaster-preparedness",
  },
];

/**
 * ReportsPage - Main page for report generation and export.
 *
 * Flow: pick a report card → form auto-selects it → choose format & dates → download.
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

  const handleCardKeyDown = useCallback(
    (e: React.KeyboardEvent, type: ReportType | null) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleCardClick(type);
      }
    },
    [handleCardClick],
  );

  return (
    <main
      className="min-h-screen bg-background"
      aria-labelledby="reports-page-heading"
    >
      {/* Skip link for keyboard users */}
      <a
        href="#report-generator"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:m-2"
      >
        Skip to report generator
      </a>

      {/* Header */}
      <header className="w-full px-6 pt-6">
        <PageHeader
          icon={FileText}
          title="Reports & Export"
          subtitle="Download flood monitoring reports as PDF or CSV files. Pick a report type below, then generate it."
        />
        <p
          className="mt-2 text-sm text-muted-foreground max-w-2xl"
          id="reports-page-heading"
        >
          <Info
            className="inline h-3.5 w-3.5 mr-1 -mt-0.5"
            aria-hidden="true"
          />
          <strong>How to use:</strong> Click any report card to select it, then
          scroll down to set your date range and download format.
        </p>
      </header>

      {/* ── Report Catalog ─────────────────────────────────────────── */}
      <section className="py-10 bg-muted/30" aria-labelledby="catalog-heading">
        <div className="w-full px-6" ref={cardsRef}>
          <SectionHeading
            label="Step 1"
            title="Choose a Report"
            subtitle="Select the type of report you need. Each card shows what data is included."
          />
          <div id="catalog-heading" className="sr-only">
            Report catalog
          </div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={cardsInView ? "show" : undefined}
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
            role="listbox"
            aria-label="Available report types"
          >
            {DISASTER_REPORTS.map((report) => {
              const Icon = report.icon;
              const isAvailable = report.reportType !== null;
              const isSelected = preselectedType === report.reportType;

              return (
                <motion.div key={report.title} variants={fadeUp}>
                  <GlassCard
                    role="option"
                    tabIndex={isAvailable ? 0 : -1}
                    aria-selected={isSelected}
                    aria-disabled={!isAvailable}
                    aria-label={`${report.title}${isSelected ? " (selected)" : ""}${!isAvailable ? " - coming soon" : ""}`}
                    className={cn(
                      "overflow-hidden transition-all duration-300 h-full flex flex-col outline-none",
                      "focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2",
                      isAvailable
                        ? "cursor-pointer hover:shadow-lg hover:ring-1 hover:ring-primary/30"
                        : "cursor-not-allowed opacity-60",
                      isSelected && "ring-2 ring-primary shadow-lg",
                    )}
                    onClick={() => handleCardClick(report.reportType)}
                    onKeyDown={(e: React.KeyboardEvent) =>
                      handleCardKeyDown(e, report.reportType)
                    }
                  >
                    <div
                      className={cn("h-1 w-full bg-linear-to-r", report.color)}
                      aria-hidden="true"
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
                          aria-hidden="true"
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
                            <CheckCircle2
                              className="h-3 w-3 mr-0.5"
                              aria-hidden="true"
                            />
                            Ready
                          </Badge>
                        ) : (
                          <Badge
                            variant="secondary"
                            className="ml-auto text-[10px] gap-0.5"
                          >
                            <Lock className="h-3 w-3" aria-hidden="true" />
                            Coming Soon
                          </Badge>
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 flex flex-col gap-3">
                      <CardDescription className="text-xs leading-relaxed">
                        {report.description}
                      </CardDescription>
                      {/* Contextual hint for more detail */}
                      <p className="text-[10px] text-muted-foreground/70 italic leading-snug">
                        {report.hint}
                      </p>
                      <div
                        className="flex flex-wrap gap-1.5"
                        aria-label="Included data sheets"
                      >
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
                      <div
                        className="mt-auto flex gap-2"
                        aria-label="Export formats"
                      >
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
                            {!fmt.available && " - soon"}
                          </Badge>
                        ))}
                      </div>
                      {isAvailable && (
                        <p className="text-[10px] text-primary/70 flex items-center gap-1 mt-1">
                          <ArrowDown className="h-3 w-3" aria-hidden="true" />
                          Click to select &amp; scroll to generator
                        </p>
                      )}
                    </CardContent>
                  </GlassCard>
                </motion.div>
              );
            })}

            {/* Data handling notice */}
            <motion.div variants={fadeUp}>
              <GlassCard
                className="overflow-hidden border-muted-foreground/20 bg-muted/10 h-full"
                role="note"
              >
                <div
                  className="h-1 w-full bg-linear-to-r from-muted-foreground/20 via-muted-foreground/40 to-muted-foreground/20"
                  aria-hidden="true"
                />
                <CardContent className="pt-5">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    <strong>About your data:</strong> Reports may include
                    location and timing information. Handle downloaded files
                    carefully and follow your organization's data handling
                    guidelines.
                  </p>
                </CardContent>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Report Generator ───────────────────────────────────────── */}
      <section
        id="report-generator"
        className="py-10 bg-background"
        ref={generatorRef}
        aria-labelledby="generator-heading"
      >
        <div className="w-full px-6">
          <div className="grid gap-8 lg:grid-cols-[1fr_350px]">
            <div className="space-y-6" ref={mainRef}>
              <SectionHeading
                label="Step 2"
                title="Generate Your Report"
                subtitle="Pick a format, set your date range, and click the download button."
              />
              <div id="generator-heading" className="sr-only">
                Report generator form
              </div>

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

            {/* ── Help sidebar ─────────────────────────────────────── */}
            <aside aria-labelledby="guide-heading">
              <SectionHeading label="Help" title="Quick Guide" />
              <div id="guide-heading" className="sr-only">
                Quick guide for report generation
              </div>

              <motion.div
                variants={staggerContainer}
                initial="hidden"
                animate={mainInView ? "show" : undefined}
                className="space-y-3"
              >
                {/* Steps card */}
                <motion.div variants={fadeUp}>
                  <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                    <div
                      className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60"
                      aria-hidden="true"
                    />
                    <div className="p-5 pb-4">
                      <div className="flex items-center gap-3">
                        <div
                          className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20"
                          aria-hidden="true"
                        >
                          <HelpCircle className="h-4 w-4 text-primary" />
                        </div>
                        <h3 className="text-sm font-semibold">
                          How to generate a report
                        </h3>
                      </div>
                    </div>
                    <div className="px-5 pb-5">
                      <ol className="list-inside list-decimal space-y-2.5 text-xs text-muted-foreground">
                        <li>
                          <strong>Pick a report</strong> - click one of the
                          cards above, or choose from the dropdown in the form.
                        </li>
                        <li>
                          <strong>Choose a format</strong> - PDF for printing or
                          sharing; CSV for opening in Excel or Google Sheets.
                        </li>
                        <li>
                          <strong>Set dates</strong> - use a quick preset (7,
                          30, or 90 days) or enter custom start and end dates.
                        </li>
                        <li>
                          <strong>Download</strong> - click &quot;Generate &amp;
                          Download&quot; and the file saves automatically.
                        </li>
                      </ol>
                    </div>
                  </GlassCard>
                </motion.div>

                {/* Format comparison card */}
                <motion.div variants={fadeUp}>
                  <GlassCard className="overflow-hidden">
                    <div
                      className="h-0.5 w-full bg-linear-to-r from-primary/40 via-primary/60 to-primary/40"
                      aria-hidden="true"
                    />
                    <CardContent className="pt-4 space-y-3">
                      <p className="text-xs font-medium">
                        Which format should I pick?
                      </p>
                      <div className="space-y-2">
                        <div className="rounded-lg border p-2.5">
                          <div className="flex items-center gap-2 text-xs font-medium">
                            <FileText
                              className="h-3.5 w-3.5"
                              aria-hidden="true"
                            />
                            PDF
                          </div>
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            Best for <strong>printing</strong> and{" "}
                            <strong>sharing</strong>. Opens with any PDF reader.
                            Includes a cover page and table of contents.
                          </p>
                        </div>
                        <div className="rounded-lg border p-2.5">
                          <div className="flex items-center gap-2 text-xs font-medium">
                            <Download
                              className="h-3.5 w-3.5"
                              aria-hidden="true"
                            />
                            CSV
                          </div>
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            Best for <strong>data analysis</strong>. Opens in
                            Excel, Google Sheets, or any spreadsheet app. Good
                            for charts and custom filtering.
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </GlassCard>
                </motion.div>

                {/* Tips card */}
                <motion.div variants={fadeUp}>
                  <GlassCard className="overflow-hidden">
                    <div
                      className="h-0.5 w-full bg-linear-to-r from-risk-safe/40 via-risk-safe/60 to-risk-safe/40"
                      aria-hidden="true"
                    />
                    <CardContent className="pt-4 space-y-2">
                      <p className="text-xs font-medium flex items-center gap-1.5">
                        <Info
                          className="h-3.5 w-3.5 text-risk-safe"
                          aria-hidden="true"
                        />
                        Tips
                      </p>
                      <ul className="text-[10px] text-muted-foreground space-y-1.5 list-disc list-inside">
                        <li>
                          Reports covering <strong>7 days or less</strong>{" "}
                          generate instantly. Longer ranges may take a few
                          seconds.
                        </li>
                        <li>
                          If a download fails, click <strong>Retry</strong> in
                          the error message - the system will try again.
                        </li>
                        <li>
                          Date ranges up to <strong>90 days</strong> are
                          supported. For longer periods, generate multiple
                          reports.
                        </li>
                      </ul>
                    </CardContent>
                  </GlassCard>
                </motion.div>
              </motion.div>
            </aside>
          </div>
        </div>
      </section>
    </main>
  );
}
