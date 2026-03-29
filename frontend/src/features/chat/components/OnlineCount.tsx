import { useEffect, useRef, useState } from "react";

import { Users } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PresenceUser } from "@/types/api/chat";

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  operator: "Operator",
  user: "Resident",
};

const ROLE_DOT: Record<string, string> = {
  admin: "bg-red-500",
  operator: "bg-amber-500",
  user: "bg-green-500",
};

interface OnlineCountProps {
  count: number;
  users?: PresenceUser[];
}

export function OnlineCount({ count, users = [] }: OnlineCountProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  if (count === 0) return null;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((p) => !p)}
        className={cn(
          "flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors",
          open && "text-foreground",
        )}
        title="View online users"
      >
        <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
        <Users className="h-3 w-3" />
        <span>{count} online</span>
      </button>

      {open && users.length > 0 && (
        <div className="absolute right-0 top-full mt-1 z-50 w-52 rounded-lg border bg-popover p-2 shadow-md animate-in fade-in-0 zoom-in-95">
          <p className="px-2 pb-1.5 text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
            Online Users
          </p>
          <ul className="max-h-48 overflow-y-auto space-y-0.5">
            {users.map((u) => (
              <li
                key={u.user_id}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-muted/50"
              >
                <div
                  className={cn(
                    "h-1.5 w-1.5 rounded-full shrink-0",
                    ROLE_DOT[u.user_role] ?? "bg-green-500",
                  )}
                />
                <span className="truncate font-medium">{u.user_name}</span>
                <span className="ml-auto text-[10px] text-muted-foreground">
                  {ROLE_LABEL[u.user_role] ?? u.user_role}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
