/**
 * Resident - My Reports Page
 *
 * Personal report history with reference numbers, status badges,
 * and detail view.
 */

import { FileText, Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMyReports } from "@/features/resident";
import { ReportCard } from "@/features/resident/components/ReportCard";
import type { CommunityReport } from "@/types";

export default function ResidentMyReportsPage() {
  const { data: reports, isLoading } = useMyReports({});

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Mga Ulat Ko / My Reports
          </h2>
          <p className="text-sm text-muted-foreground">
            Track the status of your submitted flood reports
          </p>
        </div>
        <Button asChild className="gap-2">
          <Link to="/resident/report">
            <Plus className="h-4 w-4" />
            New Report
          </Link>
        </Button>
      </div>

      {/* ── Report List ───────────────────────────────────────────── */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      ) : reports && reports.reports.length > 0 ? (
        <div className="space-y-3">
          {reports.reports.map((report: CommunityReport) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <FileText className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm font-medium">
              Wala ka pang ulat / No reports yet
            </p>
            <p className="text-xs mt-1">
              Help your community - report flooding in your area
            </p>
            <Button asChild variant="outline" size="sm" className="mt-3 gap-2">
              <Link to="/resident/report">
                <Plus className="h-4 w-4" />
                Report Flood
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
