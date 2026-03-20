/**
 * Resident — My Reports Page
 */

import { Clock, FileText, Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function ResidentMyReportsPage() {
  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto pb-24 md:pb-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">My Reports</h2>
        <Button asChild className="gap-2">
          <Link to="/resident/report">
            <Plus className="h-4 w-4" />
            New Report
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            Report History
          </CardTitle>
          <CardDescription>
            Track the status of your submitted flood reports
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Clock className="h-10 w-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">No reports submitted yet</p>
            <p className="text-xs mt-1">
              Your flood reports and their verification status will appear here
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
