/**
 * PasswordStrengthMeter - Visual password strength indicator
 *
 * Displays a segmented bar + text label indicating password strength.
 * Used in registration and password change forms.
 */

import { cn } from "@/lib/utils";

interface PasswordStrengthMeterProps {
  password: string;
}

interface StrengthLevel {
  label: string;
  color: string;
  segments: number;
}

function getPasswordStrength(password: string): StrengthLevel {
  if (!password) return { label: "", color: "", segments: 0 };

  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(password)) score++;

  if (score <= 2)
    return { label: "Weak", color: "bg-risk-critical", segments: 1 };
  if (score <= 3) return { label: "Fair", color: "bg-orange-500", segments: 2 };
  if (score <= 4) return { label: "Good", color: "bg-risk-alert", segments: 3 };
  if (score <= 5)
    return { label: "Strong", color: "bg-risk-safe", segments: 4 };
  return { label: "Excellent", color: "bg-risk-safe", segments: 5 };
}

export function PasswordStrengthMeter({
  password,
}: PasswordStrengthMeterProps) {
  const strength = getPasswordStrength(password);

  if (!password) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex gap-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-1.5 flex-1 rounded-full transition-all duration-500",
              i < strength.segments ? strength.color : "bg-muted-foreground/15",
            )}
          />
        ))}
      </div>
      <p
        className={cn(
          "text-xs font-medium transition-colors duration-300",
          strength.segments <= 1 && "text-risk-critical",
          strength.segments === 2 && "text-orange-500",
          strength.segments === 3 && "text-risk-alert",
          strength.segments >= 4 && "text-risk-safe",
        )}
      >
        {strength.label}
      </p>
    </div>
  );
}
