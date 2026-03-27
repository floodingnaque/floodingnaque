/**
 * Admin Chat Page - /admin/chat
 *
 * Multi-channel view with sidebar listing all 17 barangay channels
 * with unread indicators.  Admin-specific: broadcast to citywide,
 * pin/delete across channels, online presence overview.
 */

import { MessageSquare, Shield } from "lucide-react";
import { useCallback, useState } from "react";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Badge } from "@/components/ui/badge";
import { ChannelSidebar, ChatPanel } from "@/features/chat";

export default function AdminChatPage() {
  const [activeChannel, setActiveChannel] = useState("citywide");
  const [channelName, setChannelName] = useState("Citywide Announcements");

  const handleSelect = useCallback((id: string, name: string) => {
    setActiveChannel(id);
    setChannelName(name);
  }, []);

  return (
    <div className="p-4 sm:p-6 space-y-4 max-w-screen-2xl mx-auto">
      <Breadcrumb
        items={[
          { label: "Admin", href: "/admin" },
          { label: "Community Chat" },
        ]}
        className="mb-4"
      />
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-primary" />
            Community Chat - Admin Console
          </h2>
          <p className="text-sm text-muted-foreground">
            Monitor, moderate, and broadcast across all 17 barangay channels
          </p>
        </div>
        <Badge variant="outline" className="gap-1 text-xs">
          <Shield className="h-3 w-3" />
          Admin - full access
        </Badge>
      </div>

      {/* Sidebar + Chat */}
      <div className="flex h-[calc(100vh-200px)] min-h-100 rounded-xl border overflow-hidden">
        <ChannelSidebar
          activeChannel={activeChannel}
          onSelectChannel={handleSelect}
        />
        <div className="flex-1 min-w-0">
          <ChatPanel
            key={activeChannel}
            barangayId={activeChannel}
            channelName={channelName}
            className="h-full border-0 rounded-none"
          />
        </div>
      </div>
    </div>
  );
}
