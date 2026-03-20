/**
 * FormField — Web 3.0 Enhanced Form Input
 *
 * A polished form field with icon prefix, glassmorphism styling,
 * animated focus ring, and smooth error transitions.
 */

import { AnimatePresence, motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import * as React from "react";

import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export interface FormFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Field label */
  label: string;
  /** Lucide icon shown inside the input */
  icon?: LucideIcon;
  /** Validation error message */
  error?: string;
  /** Helper text below the input */
  helperText?: string;
  /** HTML id */
  id: string;
  /** Optional trailing element (e.g. show/hide password button) */
  trailing?: React.ReactNode;
}

const FormField = React.forwardRef<HTMLInputElement, FormFieldProps>(
  (
    { className, label, icon: Icon, error, helperText, id, trailing, ...props },
    ref,
  ) => {
    return (
      <div className="space-y-2">
        <Label htmlFor={id} className="text-sm font-medium text-foreground/90">
          {label}
        </Label>
        <div
          className={cn(
            "group relative flex items-center rounded-xl border bg-background/50 backdrop-blur-sm transition-all duration-300",
            "focus-within:ring-2 focus-within:ring-primary/30 focus-within:border-primary/50",
            "hover:border-primary/30 hover:bg-background/70",
            error
              ? "border-destructive/50 focus-within:ring-destructive/30 focus-within:border-destructive/50"
              : "border-border/50",
          )}
        >
          {Icon && (
            <div className="pointer-events-none pl-3.5 text-muted-foreground/60 transition-colors duration-300 group-focus-within:text-primary">
              <Icon className="h-4 w-4" />
            </div>
          )}
          <input
            id={id}
            ref={ref}
            className={cn(
              "flex h-11 w-full rounded-xl bg-transparent px-3.5 py-2 text-sm",
              "placeholder:text-muted-foreground/50",
              "focus-visible:outline-none",
              "disabled:cursor-not-allowed disabled:opacity-50",
              Icon && "pl-2",
              trailing && "pr-10",
              className,
            )}
            aria-invalid={!!error}
            aria-describedby={
              error ? `${id}-error` : helperText ? `${id}-helper` : undefined
            }
            {...props}
          />
          {trailing && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              {trailing}
            </div>
          )}
        </div>

        <AnimatePresence mode="wait">
          {error ? (
            <motion.p
              id={`${id}-error`}
              role="alert"
              className="text-xs font-medium text-destructive"
              initial={{ opacity: 0, y: -4, height: 0 }}
              animate={{ opacity: 1, y: 0, height: "auto" }}
              exit={{ opacity: 0, y: -4, height: 0 }}
              transition={{ duration: 0.2 }}
            >
              {error}
            </motion.p>
          ) : helperText ? (
            <motion.p
              id={`${id}-helper`}
              className="text-xs text-muted-foreground/70"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2 }}
            >
              {helperText}
            </motion.p>
          ) : null}
        </AnimatePresence>
      </div>
    );
  },
);

FormField.displayName = "FormField";

export { FormField };
