/**
 * Admin Chat Page - /admin/chat
 *
 * Multi-channel view with sidebar listing all 17 barangay channels
 * with unread indicators.  Admin-specific: broadcast to citywide,
 * pin/delete across channels, online presence overview.
 */

import { useCallback, useState } from "react";

import { ChannelSidebar, ChatPanel } from "@/features/chat";

export default function AdminChatPage() {
  const [activeChannel, setActiveChannel] = useState("citywide");
  const [channelName, setChannelName] = useState("Citywide Announcements");

  const handleSelect = useCallback((id: string, name: string) => {
    setActiveChannel(id);
    setChannelName(name);
  }, []);

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Sidebar + Chat — fills remaining height */}
      <div className="flex flex-1 min-h-0 mx-6 my-4 rounded-xl border overflow-hidden">
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
