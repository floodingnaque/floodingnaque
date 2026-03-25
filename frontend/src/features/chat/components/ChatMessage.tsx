import { formatDistanceToNow } from "date-fns";
import {
  AlertTriangle,
  FileText,
  MoreVertical,
  Pin,
  Radio,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/types/api/chat";

const MESSAGE_TYPE_CONFIG = {
  text: { icon: null, color: "", label: null },
  alert: { icon: AlertTriangle, color: "text-red-500", label: "Alert" },
  status_update: {
    icon: Radio,
    color: "text-blue-500",
    label: "Status Update",
  },
  flood_report: {
    icon: FileText,
    color: "text-cyan-500",
    label: "Flood Report",
  },
} as const;

const ROLE_BADGE_STYLES = {
  user: "bg-gray-100 text-gray-600 dark:bg-gray-800",
  operator: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  admin: "bg-purple-100 text-purple-700 dark:bg-purple-900",
} as const;

interface ChatMessageProps {
  message: ChatMessageType;
  isOwn: boolean;
  showAvatar: boolean;
  canDelete: boolean;
  canPin: boolean;
  onDelete: () => void;
  onPin: () => void;
}

export function ChatMessage({
  message,
  isOwn,
  showAvatar,
  canDelete,
  canPin,
  onDelete,
  onPin,
}: ChatMessageProps) {
  const [showActions, setShowActions] = useState(false);
  const typeConfig =
    MESSAGE_TYPE_CONFIG[message.message_type] ?? MESSAGE_TYPE_CONFIG.text;
  const TypeIcon = typeConfig.icon;

  const timeAgo = formatDistanceToNow(new Date(message.created_at), {
    addSuffix: true,
  });

  return (
    <div
      className={cn(
        "group flex gap-2 py-0.5",
        isOwn ? "flex-row-reverse" : "flex-row",
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar */}
      <div
        className={cn(
          "h-7 w-7 rounded-full shrink-0 flex items-center justify-center",
          "text-xs font-semibold text-white",
          showAvatar ? "visible" : "invisible",
          message.user_role === "operator"
            ? "bg-blue-500"
            : message.user_role === "admin"
              ? "bg-purple-500"
              : "bg-gray-400",
        )}
      >
        {message.user_name.charAt(0).toUpperCase()}
      </div>

      <div
        className={cn(
          "flex flex-col max-w-[72%]",
          isOwn ? "items-end" : "items-start",
        )}
      >
        {/* Sender line */}
        {showAvatar && (
          <div
            className={cn(
              "flex items-center gap-1.5 mb-0.5",
              isOwn ? "flex-row-reverse" : "flex-row",
            )}
          >
            <span className="text-xs font-medium">
              {isOwn ? "You" : message.user_name}
            </span>
            <span
              className={cn(
                "text-[10px] px-1 py-0.5 rounded font-medium",
                ROLE_BADGE_STYLES[message.user_role],
              )}
            >
              {message.user_role === "user" ? "resident" : message.user_role}
            </span>
            {message.is_pinned && (
              <Pin className="h-2.5 w-2.5 text-amber-500" />
            )}
          </div>
        )}

        {/* Message bubble */}
        <div
          className={cn(
            "rounded-2xl px-3 py-2 text-sm break-all",
            isOwn
              ? "bg-primary text-primary-foreground rounded-tr-sm"
              : "bg-muted rounded-tl-sm",
            message.message_type !== "text" && "border-l-4",
            message.message_type === "alert" && "border-red-500",
            message.message_type === "flood_report" && "border-cyan-500",
            message.message_type === "status_update" && "border-blue-500",
          )}
        >
          {TypeIcon && (
            <div
              className={cn(
                "flex items-center gap-1 mb-1 text-xs font-medium",
                typeConfig.color,
              )}
            >
              <TypeIcon className="h-3 w-3" />
              {typeConfig.label}
            </div>
          )}
          <p className="leading-relaxed">{message.content}</p>

          {message.report_id && (
            <Link
              to="/community"
              className="text-xs underline opacity-70 hover:opacity-100 mt-1 block"
            >
              View full report &rarr;
            </Link>
          )}
        </div>

        {/* Timestamp */}
        <span className="text-[10px] text-muted-foreground mt-0.5 px-1">
          {timeAgo}
        </span>
      </div>

      {/* Action menu for operators/admins */}
      {(canDelete || canPin) && showActions && (
        <div className={cn("self-center", isOwn ? "mr-1" : "ml-1")}>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="h-6 w-6 rounded-full flex items-center justify-center text-muted-foreground hover:bg-muted transition-colors">
                <MoreVertical className="h-3.5 w-3.5" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align={isOwn ? "end" : "start"}
              className="w-36"
            >
              {canPin && (
                <DropdownMenuItem onClick={onPin} className="text-xs">
                  <Pin className="h-3 w-3 mr-2" />
                  {message.is_pinned ? "Unpin" : "Pin"}
                </DropdownMenuItem>
              )}
              {canDelete && (
                <DropdownMenuItem
                  onClick={onDelete}
                  className="text-xs text-destructive focus:text-destructive"
                >
                  <Trash2 className="h-3 w-3 mr-2" />
                  Delete
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </div>
  );
}
