/**
 * Operator Chat Page — /operator/chat
 *
 * Multi-channel view: sidebar listing all 17 barangay channels
 * with unread indicators; main panel shows selected channel.
 */

import { MessageSquare } from "lucide-react";
import { useCallback, useState } from "react";

import { ChannelSidebar, ChatPanel } from "@/features/chat";

export default function OperatorChatPage() {
  const [activeChannel, setActiveChannel] = useState("citywide");
  const [channelName, setChannelName] = useState("Citywide Announcements");

  const handleSelect = useCallback((id: string, name: string) => {
    setActiveChannel(id);
    setChannelName(name);
  }, []);

  return (
    <div className="p-4 sm:p-6 space-y-4 max-w-screen-2xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-primary" />
          Community Chat — All Channels
        </h2>
        <p className="text-sm text-muted-foreground">
          Monitor and post to all 17 barangay channels
        </p>
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
