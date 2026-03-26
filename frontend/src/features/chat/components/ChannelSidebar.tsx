/**
 * ChannelSidebar - operator sidebar listing all 17 barangay channels
 * with unread counts, alert indicators, and channel switching.
 */

import { AlertTriangle, Hash, Megaphone } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

import { useChannelOverview } from "../hooks/useChannelOverview";

interface ChannelSidebarProps {
  activeChannel: string;
  onSelectChannel: (id: string, name: string) => void;
  className?: string;
}

export function ChannelSidebar({
  activeChannel,
  onSelectChannel,
  className,
}: ChannelSidebarProps) {
  const { channels, unreadCounts, hasAlert, totalUnread, markRead } =
    useChannelOverview();

  const handleSelect = (id: string, name: string) => {
    markRead(id);
    onSelectChannel(id, name);
  };

  return (
    <div
      className={cn(
        "flex flex-col h-full border-r bg-muted/20 w-64 shrink-0",
        className,
      )}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b">
        <h3 className="font-semibold text-sm">Channels</h3>
        {totalUnread > 0 && (
          <p className="text-xs text-muted-foreground mt-0.5">
            {totalUnread} unread message{totalUnread !== 1 ? "s" : ""}
          </p>
        )}
      </div>

      {/* Channel list */}
      <div className="flex-1 overflow-y-auto py-1">
        {channels.map((ch) => {
          const isActive = ch.barangay_id === activeChannel;
          const unread = unreadCounts[ch.barangay_id] ?? 0;
          const alert = hasAlert[ch.barangay_id] ?? false;
          const isCitywide = ch.barangay_id === "citywide";

          return (
            <button
              key={ch.barangay_id}
              onClick={() => handleSelect(ch.barangay_id, ch.display_name)}
              className={cn(
                "w-full flex items-center gap-2 px-4 py-2 text-left text-sm transition-colors",
                "hover:bg-muted/50",
                isActive && "bg-muted font-medium",
              )}
            >
              {isCitywide ? (
                <Megaphone className="h-3.5 w-3.5 text-amber-500 shrink-0" />
              ) : (
                <Hash className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              )}

              <span className="flex-1 truncate">{ch.display_name}</span>

              {alert && (
                <AlertTriangle className="h-3.5 w-3.5 text-red-500 shrink-0 animate-pulse" />
              )}

              {unread > 0 && (
                <Badge
                  variant="destructive"
                  className="h-5 min-w-5 px-1.5 text-[10px] font-bold"
                >
                  {unread > 99 ? "99+" : unread}
                </Badge>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
