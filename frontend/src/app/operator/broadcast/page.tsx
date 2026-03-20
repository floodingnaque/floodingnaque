/**
 * Operator — Broadcast Center Page
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Mail, MessageSquare, Radio, Send, Smartphone } from "lucide-react";

export default function OperatorBroadcastPage() {
  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Compose Broadcast */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Send className="h-4 w-4 text-primary" />
            Compose Broadcast
          </CardTitle>
          <CardDescription>
            Send emergency communications to residents via multiple channels
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Target Selection */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Target Barangays</p>
            <div className="flex flex-wrap gap-2">
              <Badge
                variant="outline"
                className="cursor-pointer hover:bg-primary/10"
              >
                All Barangays
              </Badge>
              <Badge
                variant="outline"
                className="cursor-pointer hover:bg-red-500/10 text-red-600"
              >
                All Critical
              </Badge>
              <Badge
                variant="outline"
                className="cursor-pointer hover:bg-amber-500/10 text-amber-600"
              >
                All Alert-Level
              </Badge>
            </div>
          </div>

          {/* Channel Selection */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Broadcast Channels</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[
                {
                  icon: Smartphone,
                  label: "SMS",
                  desc: "Text message to residents",
                },
                { icon: Mail, label: "Email", desc: "Email notification" },
                {
                  icon: MessageSquare,
                  label: "Push",
                  desc: "Browser push notification",
                },
                {
                  icon: Radio,
                  label: "SSE / In-App",
                  desc: "Real-time in-app alert",
                },
              ].map((ch) => (
                <button
                  key={ch.label}
                  className="flex items-center gap-3 p-3 rounded-lg border border-border/50 hover:bg-accent transition-colors text-left"
                >
                  <ch.icon className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">{ch.label}</p>
                    <p className="text-xs text-muted-foreground">{ch.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Message */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Message</p>
            <textarea
              className="w-full min-h-32 p-3 rounded-lg border border-border/50 bg-background text-sm resize-y focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Type your broadcast message here... Use {{barangay}}, {{risk_level}}, {{timestamp}} for auto-fill."
            />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Supports template variables</span>
              <span>0 / 160 characters (SMS)</span>
            </div>
          </div>

          <Button className="w-full sm:w-auto gap-2">
            <Send className="h-4 w-4" />
            Send Broadcast
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
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Send className="h-10 w-10 mb-2 opacity-30" />
            <p className="text-sm">No broadcasts sent yet</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
