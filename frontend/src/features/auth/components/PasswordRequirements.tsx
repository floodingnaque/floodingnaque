/**
 * PasswordRequirements - Real-time password validation checklist
 *
 * Displays a list of password criteria that check off in real-time
 * as the user types. Used in registration and password reset forms.
 */

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { Check, X } from "lucide-react";

interface Requirement {
  label: string;
  met: boolean;
}

interface PasswordRequirementsProps {
  password: string;
}

function getRequirements(password: string): Requirement[] {
  return [
    { label: "At least 8 characters", met: password.length >= 8 },
    { label: "Contains uppercase letter", met: /[A-Z]/.test(password) },
    { label: "Contains lowercase letter", met: /[a-z]/.test(password) },
    { label: "Contains a number", met: /[0-9]/.test(password) },
    {
      label: "Contains special character",
      met: /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(password),
    },
  ];
}

export function PasswordRequirements({ password }: PasswordRequirementsProps) {
  const requirements = getRequirements(password);

  if (!password) return null;

  return (
    <motion.ul
      className="space-y-1.5 mt-2"
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      transition={{ duration: 0.2 }}
      aria-label="Password requirements"
    >
      {requirements.map((req) => (
        <li
          key={req.label}
          className={cn(
            "flex items-center gap-2 text-xs transition-colors duration-200",
            req.met ? "text-risk-safe" : "text-muted-foreground/60",
          )}
        >
          {req.met ? (
            <Check className="h-3 w-3 shrink-0" />
          ) : (
            <X className="h-3 w-3 shrink-0" />
          )}
          {req.label}
        </li>
      ))}
    </motion.ul>
  );
}
