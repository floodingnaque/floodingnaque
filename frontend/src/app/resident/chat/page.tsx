/**
 * Resident Chat Page — /resident/chat
 *
 * Shows the user's barangay channel + citywide channel.
 * Fetches the user's barangay from their profile via the API,
 * with a fallback selector if not set.
 */

import { MessageSquare } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { BARANGAYS } from "@/config/paranaque";
import { ChatPanel } from "@/features/chat";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";

/** Barangay display name map (key → name) */
const BARANGAY_NAMES: Record<string, string> = Object.fromEntries(
  BARANGAYS.map((b) => [b.key, b.name]),
);

export default function ResidentChatPage() {
  const [userBarangay, setUserBarangay] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"barangay" | "citywide">(
    "barangay",
  );

  // Fetch channels to discover user's assigned barangay
  useEffect(() => {
    let cancelled = false;
    api
      .get<{ channels: { barangay_id: string }[] }>("/api/v1/chat/channels")
      .then((data) => {
        if (cancelled) return;
        // Find first non-citywide channel (that's the user's barangay)
        const brgy = data.channels?.find((c) => c.barangay_id !== "citywide");
        if (brgy) setUserBarangay(brgy.barangay_id);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSelectBarangay = useCallback((key: string) => {
    setUserBarangay(key);
  }, []);

  if (isLoading) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 space-y-4 w-full">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-125 w-full rounded-xl" />
      </div>
    );
  }

  // If user has no barangay assigned, show a selector
  if (!userBarangay) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 space-y-4 w-full">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-primary" />
              Community Chat
            </CardTitle>
            <CardDescription>
              Select your barangay to join the community chat
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Select onValueChange={handleSelectBarangay}>
              <SelectTrigger className="w-64">
                <SelectValue placeholder="Choose your barangay..." />
              </SelectTrigger>
              <SelectContent>
                {BARANGAYS.map((b) => (
                  <SelectItem key={b.key} value={b.key}>
                    {b.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      </div>
    );
  }

  const barangayName = BARANGAY_NAMES[userBarangay] ?? userBarangay;

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-4 w-full">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-primary" />
          Community Chat
        </h2>
        <p className="text-sm text-muted-foreground">
          Stay connected with your barangay and get city-wide announcements
        </p>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab("barangay")}
          className={cn(
            "px-4 py-2 text-sm rounded-lg transition-colors",
            activeTab === "barangay"
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-muted/80",
          )}
        >
          {barangayName}
        </button>
        <button
          onClick={() => setActiveTab("citywide")}
          className={cn(
            "px-4 py-2 text-sm rounded-lg transition-colors flex items-center gap-1.5",
            activeTab === "citywide"
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-muted/80",
          )}
        >
          Citywide
          <Badge variant="outline" className="text-[10px] px-1.5">
            Broadcast
          </Badge>
        </button>
      </div>

      {/* Chat panel */}
      <div className="h-[calc(100vh-280px)] min-h-100">
        {activeTab === "barangay" ? (
          <ChatPanel
            key={userBarangay}
            barangayId={userBarangay}
            channelName={barangayName}
            className="h-full"
          />
        ) : (
          <ChatPanel
            key="citywide"
            barangayId="citywide"
            channelName="Citywide Announcements"
            className="h-full"
          />
        )}
      </div>
    </div>
  );
}
