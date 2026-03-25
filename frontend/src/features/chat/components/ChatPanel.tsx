/**
 * ChatPanel — main chat interface for a single barangay channel.
 *
 * Used in both resident and operator dashboards.
 */

import { ChevronUp, Pin, RefreshCw, Send, Wifi, WifiOff } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/state/stores/authStore";

import { useChat } from "../hooks/useChat";
import { ChatMessage } from "./ChatMessage";
import { OnlineCount } from "./OnlineCount";
import { TypingIndicator } from "./TypingIndicator";

interface ChatPanelProps {
  barangayId: string;
  channelName: string;
  className?: string;
}

export function ChatPanel({
  barangayId,
  channelName,
  className,
}: ChatPanelProps) {
  const user = useAuthStore((s) => s.user);
  const {
    messages,
    pinnedMessages,
    onlineUsers,
    typingUsers,
    isConnected,
    isLoading,
    hasMore,
    error,
    sendMessage,
    sendTyping,
    deleteMessage,
    togglePin,
    loadOlderMessages,
    reconnect,
  } = useChat(barangayId);

  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [showPinned, setShowPinned] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const typingDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isAtBottom = useRef(true);

  // Auto-scroll on new messages
  useEffect(() => {
    if (isAtBottom.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    isAtBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (el.scrollTop < 50 && hasMore) {
      loadOlderMessages();
    }
  }, [hasMore, loadOlderMessages]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setInput(e.target.value);
      sendTyping(true);
      if (typingDebounce.current) clearTimeout(typingDebounce.current);
      typingDebounce.current = setTimeout(() => sendTyping(false), 2000);
    },
    [sendTyping],
  );

  const handleSend = useCallback(async () => {
    if (!input.trim() || isSending) return;
    setIsSending(true);
    try {
      await sendMessage(input);
      setInput("");
      sendTyping(false);
      if (typingDebounce.current) clearTimeout(typingDebounce.current);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  }, [input, isSending, sendMessage, sendTyping]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const canPost = barangayId !== "citywide" || user?.role !== "user";

  return (
    <div
      className={cn(
        "flex flex-col h-full bg-background border rounded-xl overflow-hidden",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-sm">{channelName}</h3>
          {barangayId === "citywide" && (
            <Badge variant="outline" className="text-xs">
              Broadcast
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-3">
          {pinnedMessages.length > 0 && (
            <button
              onClick={() => setShowPinned((p) => !p)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <Pin className="h-3 w-3" />
              {pinnedMessages.length} pinned
            </button>
          )}
          <OnlineCount count={onlineUsers.length} />
          <div className="flex items-center gap-1">
            {isConnected ? (
              <Wifi className="h-3.5 w-3.5 text-green-500" />
            ) : (
              <WifiOff className="h-3.5 w-3.5 text-red-500 animate-pulse" />
            )}
            <span className="text-xs text-muted-foreground">
              {isConnected ? "Live" : "Reconnecting..."}
            </span>
            {!isConnected && (
              <button
                onClick={reconnect}
                className="ml-1 text-muted-foreground hover:text-foreground transition-colors"
                title="Retry connection"
              >
                <RefreshCw className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-4 py-2 bg-destructive/10 border-b border-destructive/20 flex items-center justify-between">
          <p className="text-xs text-destructive">{error}</p>
          <button
            onClick={reconnect}
            className="text-xs text-destructive font-medium hover:underline flex items-center gap-1"
          >
            <RefreshCw className="h-3 w-3" />
            Retry
          </button>
        </div>
      )}

      {/* Pinned messages banner */}
      {showPinned && pinnedMessages.length > 0 && (
        <div className="border-b bg-amber-50 dark:bg-amber-950/20 px-4 py-2">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-1 flex items-center gap-1">
            <Pin className="h-3 w-3" /> Pinned Messages
          </p>
          {pinnedMessages.map((msg) => (
            <p key={msg.id} className="text-xs text-muted-foreground truncate">
              <span className="font-medium">{msg.user_name}:</span>{" "}
              {msg.content}
            </p>
          ))}
        </div>
      )}

      {/* Load more */}
      {hasMore && (
        <button
          onClick={loadOlderMessages}
          className="flex items-center justify-center gap-1 py-2 text-xs text-muted-foreground hover:text-foreground border-b transition-colors"
        >
          <ChevronUp className="h-3 w-3" />
          Load older messages
        </button>
      )}

      {/* Messages area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-3"
        onScroll={handleScroll}
      >
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-sm text-muted-foreground">
              Loading messages...
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-muted-foreground">
            <p className="text-sm">No messages yet.</p>
            {canPost && (
              <p className="text-xs">Be the first to post in {channelName}</p>
            )}
          </div>
        ) : (
          <div className="space-y-1">
            {messages.map((msg, idx) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                isOwn={msg.user_id === user?.id}
                showAvatar={
                  idx === 0 || messages[idx - 1]?.user_id !== msg.user_id
                }
                canDelete={user?.role === "operator" || user?.role === "admin"}
                canPin={user?.role === "operator" || user?.role === "admin"}
                onDelete={() => deleteMessage(msg.id)}
                onPin={() => togglePin(msg.id)}
              />
            ))}
            {typingUsers.length > 0 && <TypingIndicator users={typingUsers} />}
          </div>
        )}
      </div>

      {/* Input area */}
      {canPost ? (
        <div className="px-4 py-3 border-t bg-background">
          {barangayId === "citywide" && (
            <p className="text-xs text-amber-600 dark:text-amber-400 mb-2">
              Broadcasting to all 16 barangays
            </p>
          )}
          <div className="flex gap-2">
            <Input
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={
                barangayId === "citywide"
                  ? "Type a city-wide announcement..."
                  : `Message ${channelName}...`
              }
              maxLength={1000}
              disabled={!isConnected || isSending}
              className="flex-1 rounded-xl"
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || !isConnected || isSending}
              size="icon"
              className="rounded-xl shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          {input.length > 900 && (
            <p className="text-xs text-muted-foreground mt-1 text-right">
              {input.length}/1000
            </p>
          )}
        </div>
      ) : (
        <div className="px-4 py-3 border-t bg-muted/30">
          <p className="text-xs text-center text-muted-foreground">
            This is a read-only broadcast channel
          </p>
        </div>
      )}
    </div>
  );
}
