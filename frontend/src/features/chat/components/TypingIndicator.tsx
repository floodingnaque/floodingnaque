interface TypingUser {
  name: string;
  role: string;
}

function formatUser(u: TypingUser) {
  const tag =
    u.role === "admin" ? "Admin" : u.role === "operator" ? "Operator" : "";
  return tag ? `${tag} ${u.name}` : u.name;
}

export function TypingIndicator({ users }: { users: TypingUser[] }) {
  const label =
    users.length === 1
      ? `${formatUser(users[0])} is typing`
      : users.length === 2
        ? `${formatUser(users[0])} and ${formatUser(users[1])} are typing`
        : `${users.length} people are typing`;

  return (
    <div className="flex items-center gap-2 px-2 py-1">
      <div className="flex gap-0.5">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50 animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
      <span className="text-xs text-muted-foreground italic">{label}</span>
    </div>
  );
}
