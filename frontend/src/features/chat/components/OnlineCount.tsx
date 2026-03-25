import { Users } from "lucide-react";

export function OnlineCount({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <div className="flex items-center gap-1 text-xs text-muted-foreground">
      <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
      <Users className="h-3 w-3" />
      <span>{count} online</span>
    </div>
  );
}
