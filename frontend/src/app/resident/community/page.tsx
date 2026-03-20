/**
 * Resident — Community Reports Page
 */

import { MessageSquare } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function ResidentCommunityPage() {
  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto pb-24 md:pb-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-primary" />
            Community Reports
          </CardTitle>
          <CardDescription>
            Verified flood reports from other residents in Parañaque
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Empty state */}
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <MessageSquare className="h-10 w-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">No community reports yet</p>
            <p className="text-xs mt-1">
              Be the first to report — help others stay safe
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
