/**
 * Reports Page
 *
 * Page for generating and exporting reports in various formats.
 * Provides access to prediction, alert, and weather data exports.
 */

import { FileText, HelpCircle, Download, Database, BarChart3, Bell } from 'lucide-react';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { ReportGenerator } from '@/features/reports/components/ReportGenerator';

/**
 * Report types with their descriptions
 */
const REPORT_INFO = [
  {
    icon: BarChart3,
    title: 'Predictions Report',
    description:
      'Export flood prediction history including risk levels, confidence scores, and timestamps.',
  },
  {
    icon: Bell,
    title: 'Alerts Report',
    description:
      'Download alert history with triggered times, locations, acknowledgment status, and severity.',
  },
  {
    icon: Database,
    title: 'Weather Report',
    description:
      'Export weather observations and forecast data including temperature, rainfall, and humidity.',
  },
];

/**
 * ReportsPage - Main page for report generation and export
 */
export default function ReportsPage() {
  return (
    <div className="container mx-auto space-y-8 py-8">
      {/* Page Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Reports & Export</h1>
            <p className="text-muted-foreground">
              Generate and download reports for analysis and record keeping
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_350px]">
        {/* Report Generator */}
        <div className="space-y-6">
          <ReportGenerator />

          {/* Help Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <HelpCircle className="h-5 w-5" />
                Report Guide
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <h4 className="font-medium">How to Generate Reports</h4>
                <ol className="list-inside list-decimal space-y-2 text-sm text-muted-foreground">
                  <li>Select the type of report you want to generate</li>
                  <li>Choose your preferred export format (PDF or CSV)</li>
                  <li>
                    Optionally select a date range to filter the data, or use quick
                    presets
                  </li>
                  <li>
                    Click "Generate & Download" to create and save your report
                  </li>
                </ol>
              </div>

              <div className="space-y-3">
                <h4 className="font-medium">Format Comparison</h4>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border p-3">
                    <div className="flex items-center gap-2 font-medium">
                      <FileText className="h-4 w-4 text-foreground" />
                      PDF Format
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Best for printing, presentations, and formal documentation.
                      Includes charts and formatted tables.
                    </p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <div className="flex items-center gap-2 font-medium">
                      <Download className="h-4 w-4 text-foreground" />
                      CSV Format
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Best for data analysis in Excel, Google Sheets, or other
                      spreadsheet applications.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Available Reports Sidebar */}
        <div className="space-y-4">
          <h3 className="font-semibold">Available Reports</h3>
          <div className="space-y-3">
            {REPORT_INFO.map((report, index) => (
              <Card key={index} className="transition-colors hover:bg-muted/50">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <report.icon className="h-4 w-4 text-primary" />
                    {report.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{report.description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Data Privacy Notice */}
          <Card className="border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950">
            <CardContent className="pt-4">
              <p className="text-xs text-amber-800 dark:text-amber-200">
                <strong>Privacy Notice:</strong> Exported reports may contain
                sensitive location and timing data. Please handle exported files
                responsibly and in accordance with data protection guidelines.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
