/**
 * Operator - Broadcast Center Page
 *
 * Functional broadcast page with real SMS/email dispatch via the
 * POST /api/v1/lgu/broadcasts endpoint.
 */

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";
import { showToast } from "@/lib/toast";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle,
  Loader2,
  Mail,
  Radio,
  Send,
  Smartphone,
  XCircle,
} from "lucide-react";
import { useCallback, useState } from "react";

// ── Constants ───────────────────────────────────────────────────────────

const PARANAQUE_BARANGAYS = [
  "Baclaran",
  "BF Homes",
  "Don Bosco",
  "Don Galo",
  "La Huerta",
  "Marcelo Green Village",
  "Merville",
  "Moonwalk",
  "San Antonio",
  "San Dionisio",
  "San Isidro",
  "San Martin de Porres",
  "Santo Niño",
  "Sun Valley",
  "Tambo",
  "Vitalez",
] as const;

const CHANNELS = [
  {
    id: "sms",
    icon: Smartphone,
    label: "SMS",
    desc: "Text message to residents",
  },
  { id: "email", icon: Mail, label: "Email", desc: "Email notification" },
  {
    id: "sse",
    icon: Radio,
    label: "SSE / In-App",
    desc: "Real-time in-app alert",
  },
] as const;

const PRIORITIES = ["low", "normal", "high", "critical"] as const;

const SMS_CHAR_LIMIT = 160;

// ── Types ───────────────────────────────────────────────────────────────

interface BroadcastRecord {
  id: number;
  title: string | null;
  message: string;
  priority: string;
  target_barangays: string[];
  channels: string[];
  recipients: number;
  sent_by: string;
  incident_id: number | null;
  sent_at: string;
}

interface BroadcastResponse {
  success: boolean;
  data: {
    broadcast_id: number;
    recipients: number;
    delivery_results: Record<string, string>;
  };
}

interface BroadcastListResponse {
  success: boolean;
  data: BroadcastRecord[];
  pagination: { total: number; limit: number; offset: number };
}

// ── Component ───────────────────────────────────────────────────────────

export default function OperatorBroadcastPage() {
  const queryClient = useQueryClient();

  // Form state
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [priority, setPriority] = useState<string>("normal");
  const [selectedBarangays, setSelectedBarangays] = useState<string[]>([]);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);

  // Broadcast history
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ["broadcasts"],
    queryFn: () =>
      api.get<BroadcastListResponse>(API_ENDPOINTS.lgu.broadcasts, {
        params: { limit: 20 },
      }),
    refetchInterval: 30_000,
  });

  // Send broadcast mutation
  const sendMutation = useMutation({
    mutationFn: (payload: {
      title: string;
      message: string;
      priority: string;
      target_barangays: string[];
      channels: string[];
    }) => api.post<BroadcastResponse>(API_ENDPOINTS.lgu.broadcasts, payload),
    onSuccess: (data) => {
      const results = data.data.delivery_results;
      const summary = Object.entries(results)
        .map(([ch, status]) => `${ch}: ${status}`)
        .join(", ");
      showToast.success(
        `Broadcast sent to ${data.data.recipients} recipients (${summary})`,
      );
      queryClient.invalidateQueries({ queryKey: ["broadcasts"] });
      // Reset form
      setTitle("");
      setMessage("");
      setPriority("normal");
      setSelectedBarangays([]);
      setSelectedChannels([]);
    },
    onError: () => {
      showToast.error("Failed to send broadcast. Check the server logs.");
    },
  });

  // Barangay toggle
  const toggleBarangay = useCallback((name: string) => {
    setSelectedBarangays((prev) =>
      prev.includes(name) ? prev.filter((b) => b !== name) : [...prev, name],
    );
  }, []);

  const selectAllBarangays = useCallback(
    () => setSelectedBarangays([...PARANAQUE_BARANGAYS]),
    [],
  );
  const clearBarangays = useCallback(() => setSelectedBarangays([]), []);

  // Channel toggle
  const toggleChannel = useCallback((id: string) => {
    setSelectedChannels((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
  }, []);

  // Send handler
  const handleSend = () => {
    if (!message.trim()) {
      showToast.warning("Message cannot be empty.");
      return;
    }
    if (selectedBarangays.length === 0) {
      showToast.warning("Select at least one barangay.");
      return;
    }
    if (selectedChannels.length === 0) {
      showToast.warning("Select at least one channel.");
      return;
    }
    sendMutation.mutate({
      title: title.trim() || "Flood Alert Broadcast",
      message: message.trim(),
      priority,
      target_barangays: selectedBarangays,
      channels: selectedChannels,
    });
  };

  const canSend =
    message.trim().length > 0 &&
    selectedBarangays.length > 0 &&
    selectedChannels.length > 0 &&
    !sendMutation.isPending;

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <Breadcrumb
        items={[
          { label: "Operations", href: "/operator" },
          { label: "Broadcast Center" },
        ]}
        className="mb-4"
      />

      {/* Compose Broadcast */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Send className="h-4 w-4 text-primary" />
            Compose Broadcast
          </CardTitle>
          <CardDescription>
            Send emergency communications to residents via SMS, email, or in-app
            channels
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Title */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Title (optional)</p>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Flood Alert - Heavy Rainfall Warning"
              className="w-full p-2 rounded-lg border border-border/50 bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {/* Priority */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Priority</p>
            <div className="flex flex-wrap gap-2">
              {PRIORITIES.map((p) => (
                <Badge
                  key={p}
                  variant={priority === p ? "default" : "outline"}
                  className={`cursor-pointer capitalize ${
                    priority === p
                      ? p === "critical"
                        ? "bg-red-600 text-white"
                        : p === "high"
                          ? "bg-amber-500 text-white"
                          : ""
                      : ""
                  }`}
                  onClick={() => setPriority(p)}
                >
                  {p}
                </Badge>
              ))}
            </div>
          </div>

          {/* Target Selection */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">
                Target Barangays ({selectedBarangays.length}/
                {PARANAQUE_BARANGAYS.length})
              </p>
              <div className="flex gap-2">
                <button
                  className="text-xs text-primary hover:underline"
                  onClick={selectAllBarangays}
                >
                  Select All
                </button>
                <button
                  className="text-xs text-muted-foreground hover:underline"
                  onClick={clearBarangays}
                >
                  Clear
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {PARANAQUE_BARANGAYS.map((name) => (
                <Badge
                  key={name}
                  variant={
                    selectedBarangays.includes(name) ? "default" : "outline"
                  }
                  className="cursor-pointer"
                  onClick={() => toggleBarangay(name)}
                >
                  {name}
                </Badge>
              ))}
            </div>
          </div>

          {/* Channel Selection */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Broadcast Channels</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {CHANNELS.map((ch) => {
                const selected = selectedChannels.includes(ch.id);
                return (
                  <button
                    key={ch.id}
                    onClick={() => toggleChannel(ch.id)}
                    className={`flex items-center gap-3 p-3 rounded-lg border transition-colors text-left ${
                      selected
                        ? "border-primary bg-primary/10"
                        : "border-border/50 hover:bg-accent"
                    }`}
                  >
                    <ch.icon
                      className={`h-5 w-5 ${selected ? "text-primary" : "text-muted-foreground"}`}
                    />
                    <div>
                      <p className="text-sm font-medium">{ch.label}</p>
                      <p className="text-xs text-muted-foreground">{ch.desc}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Message */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Message</p>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="w-full min-h-32 p-3 rounded-lg border border-border/50 bg-background text-sm resize-y focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Type your broadcast message here..."
            />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {selectedChannels.includes("sms") &&
                  message.length > SMS_CHAR_LIMIT && (
                    <span className="text-amber-500">
                      SMS messages over {SMS_CHAR_LIMIT} chars may use multiple
                      credits.{" "}
                    </span>
                  )}
              </span>
              <span
                className={
                  selectedChannels.includes("sms") &&
                  message.length > SMS_CHAR_LIMIT
                    ? "text-amber-500 font-medium"
                    : ""
                }
              >
                {message.length} / {SMS_CHAR_LIMIT} characters (SMS)
              </span>
            </div>
          </div>

          <Button
            className="w-full sm:w-auto gap-2"
            onClick={handleSend}
            disabled={!canSend}
          >
            {sendMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {sendMutation.isPending ? "Sending..." : "Send Broadcast"}
          </Button>
        </CardContent>
      </Card>

      {/* Broadcast History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Broadcast History</CardTitle>
          <CardDescription>Past broadcasts and delivery status</CardDescription>
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              <span className="text-sm">Loading history...</span>
            </div>
          ) : historyData?.data && historyData.data.length > 0 ? (
            <div className="space-y-3">
              {historyData.data.map((b) => (
                <div
                  key={b.id}
                  className="flex items-start gap-3 p-3 rounded-lg border border-border/50"
                >
                  <div className="mt-0.5">
                    {b.recipients > 0 ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium truncate">
                        {b.title || "Untitled Broadcast"}
                      </span>
                      <Badge
                        variant="outline"
                        className={`text-xs capitalize ${
                          b.priority === "critical"
                            ? "text-red-600 dark:text-red-400 border-red-300"
                            : b.priority === "high"
                              ? "text-amber-600 dark:text-amber-400 border-amber-300"
                              : ""
                        }`}
                      >
                        {b.priority}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {b.message}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                      <span>
                        {b.channels.map((c) => c.toUpperCase()).join(", ")}
                      </span>
                      <span>{b.recipients} recipients</span>
                      <span>
                        {b.target_barangays.length > 2
                          ? `${b.target_barangays.slice(0, 2).join(", ")} +${b.target_barangays.length - 2}`
                          : b.target_barangays.join(", ")}
                      </span>
                      <span className="ml-auto">
                        {b.sent_at
                          ? new Date(b.sent_at).toLocaleString("en-PH", {
                              dateStyle: "short",
                              timeStyle: "short",
                            })
                          : "-"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Send className="h-10 w-10 mb-2 opacity-30" />
              <p className="text-sm">No broadcasts sent yet</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
