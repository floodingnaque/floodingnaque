/**
 * CityWideBroadcastSection - Read-only live feed of city-wide broadcast
 * messages on the landing page.
 *
 * Subscribes to the "citywide" chat channel via Supabase Realtime for
 * live updates, with initial history loaded from the Flask REST API.
 * No message input - completely read-only for all visitors.
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api-client";
import { isRealtimeEnabled, supabase } from "@/lib/supabase";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/api/chat";
import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  Bell,
  Megaphone,
  Radio,
  ShieldAlert,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

// ── Constants ────────────────────────────────────────────────────────────

const INITIAL_LIMIT = 10;

const TYPE_CONFIG: Record<
  string,
  { icon: typeof Bell; cls: string; label: string }
> = {
  alert: {
    icon: AlertTriangle,
    cls: "bg-risk-alert/10 text-risk-alert border-risk-alert/30",
    label: "Alert",
  },
  flood_report: {
    icon: ShieldAlert,
    cls: "bg-risk-critical/10 text-risk-critical border-risk-critical/30",
    label: "Flood Report",
  },
  status_update: {
    icon: Radio,
    cls: "bg-primary/10 text-primary border-primary/30",
    label: "Status Update",
  },
  text: {
    icon: Megaphone,
    cls: "bg-muted text-muted-foreground border-muted-foreground/30",
    label: "Announcement",
  },
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// ── Component ────────────────────────────────────────────────────────────

export function CityWideBroadcastSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(sectionRef, { once: true, amount: 0.15 });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);

  // ── Load initial history ───────────────────────────────────────
  const loadHistory = useCallback(async () => {
    try {
      const data = await api.get<{
        messages: ChatMessage[];
        has_more: boolean;
      }>(`/api/v1/chat/citywide/public?limit=${INITIAL_LIMIT}`);
      setMessages(data.messages);
    } catch {
      // Graceful: section simply shows empty state
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ── Subscribe to Realtime ──────────────────────────────────────
  useEffect(() => {
    if (!isInView) return;
    loadHistory();

    if (!isRealtimeEnabled) return;

    const channel = supabase
      .channel("landing:citywide", {
        config: { presence: { key: "landing" } },
      })
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "chat_messages",
          filter: "barangay_id=eq.citywide",
        },
        (payload) => {
          const msg = payload.new as ChatMessage;
          setMessages((prev) => {
            if (prev.some((m) => m.id === msg.id)) return prev;
            // Keep only latest INITIAL_LIMIT messages
            const next = [...prev, msg];
            return next.length > INITIAL_LIMIT
              ? next.slice(-INITIAL_LIMIT)
              : next;
          });
        },
      )
      .subscribe((status) => {
        setIsLive(status === "SUBSCRIBED");
      });

    return () => {
      channel.unsubscribe();
    };
  }, [isInView, loadHistory]);

  // ── Render ─────────────────────────────────────────────────────
  return (
    <section
      id="broadcast"
      className="py-20 sm:py-24 bg-muted/30"
      ref={sectionRef}
      aria-labelledby="broadcast-heading"
    >
      <div className="container mx-auto px-4">
        {/* Heading */}
        <div className="text-center mb-10">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary mb-3">
            Live Feed
          </p>
          <h2
            id="broadcast-heading"
            className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight"
          >
            City-Wide Broadcast
          </h2>
          <p className="mt-3 text-muted-foreground max-w-lg mx-auto leading-relaxed">
            Real-time announcements and alerts from Parañaque DRRMO operators -
            visible to everyone, no login required.
          </p>
        </div>

        {/* Connection indicator */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {isLive ? (
            <>
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
              </span>
              <span className="text-xs text-green-600 dark:text-green-400 font-medium flex items-center gap-1">
                <Wifi className="h-3 w-3" /> Live updates active
              </span>
            </>
          ) : (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <WifiOff className="h-3 w-3" /> Showing recent messages
            </span>
          )}
        </div>

        {/* Message feed */}
        <div
          className="max-w-2xl mx-auto space-y-3"
          role="log"
          aria-live="polite"
          aria-label="City-wide broadcast messages"
        >
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Card key={i} className="overflow-hidden">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <Skeleton className="h-8 w-8 rounded-full shrink-0" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-3 w-full" />
                      <Skeleton className="h-3 w-2/3" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : undefined}
              transition={{ duration: 0.4 }}
            >
              <Card className="border-dashed">
                <CardContent className="py-10 text-center">
                  <Megaphone className="h-10 w-10 text-muted-foreground/40 mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground">
                    No broadcast messages yet. Announcements from DRRMO
                    operators will appear here in real-time.
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          ) : (
            messages.map((msg, idx) => {
              const config = TYPE_CONFIG[msg.message_type] ?? TYPE_CONFIG.text!;
              const Icon = config!.icon;

              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 15 }}
                  animate={isInView ? { opacity: 1, y: 0 } : undefined}
                  transition={{ duration: 0.35, delay: idx * 0.05 }}
                >
                  <Card
                    className={cn(
                      "overflow-hidden transition-shadow hover:shadow-md",
                      msg.message_type === "alert" && "border-risk-alert/30",
                      msg.message_type === "flood_report" &&
                        "border-risk-critical/30",
                    )}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        {/* Icon */}
                        <div
                          className={cn(
                            "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                            config.cls,
                          )}
                        >
                          <Icon className="h-4 w-4" />
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-semibold text-foreground">
                              {msg.user_name}
                            </span>
                            {msg.user_role && msg.user_role !== "user" && (
                              <Badge
                                variant="outline"
                                className="text-[10px] px-1.5 py-0"
                              >
                                {msg.user_role === "admin"
                                  ? "Admin"
                                  : "Operator"}
                              </Badge>
                            )}
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-[10px] px-1.5 py-0",
                                config.cls,
                              )}
                            >
                              {config.label}
                            </Badge>
                            <span className="text-xs text-muted-foreground ml-auto shrink-0">
                              {timeAgo(msg.created_at)}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-foreground/85 leading-relaxed wrap-break-word">
                            {msg.content}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })
          )}
        </div>

        {/* Read-only notice */}
        <p className="text-center text-xs text-muted-foreground mt-6">
          This is a read-only feed.{" "}
          <a
            href="/login"
            className="text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-sm"
          >
            Sign in
          </a>{" "}
          to access your barangay chat channel.
        </p>
      </div>
    </section>
  );
}

export default CityWideBroadcastSection;
