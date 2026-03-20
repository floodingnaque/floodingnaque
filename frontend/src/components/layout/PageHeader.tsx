/**
 * PageHeader — Landing-page-inspired page header
 *
 * A dark navy rounded banner with icon, title, subtitle,
 * and optional right-side action area. Matches the design language
 * of the dashboard hero banners but is compact enough for utility pages.
 *
 * Usage:
 * ```tsx
 * <PageHeader
 *   icon={Shield}
 *   title="Admin Panel"
 *   subtitle="System health monitoring and statistics"
 *   actions={<Button>Refresh</Button>}
 * />
 * ```
 */

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

interface PageHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  /** Optional badge / tag rendered next to the title */
  badge?: React.ReactNode;
  /** Right-side actions (buttons, connection status, etc.) */
  actions?: React.ReactNode;
  /** Additional className applied to the outer wrapper */
  className?: string;
}

export function PageHeader({
  icon: Icon,
  title,
  subtitle,
  badge,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      className={cn(
        "relative rounded-2xl bg-primary overflow-hidden",
        className,
      )}
    >
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-linear-to-br from-white/5 via-transparent to-black/10" />

      <div className="relative z-10 px-6 py-6 sm:px-8 sm:py-7">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          {/* Left: Icon + Title */}
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 flex items-center justify-center shrink-0">
              <Icon className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                  {title}
                </h1>
                {badge}
              </div>
              {subtitle && (
                <p className="text-sm text-white/70 mt-0.5">{subtitle}</p>
              )}
            </div>
          </div>

          {/* Right: Actions */}
          {actions && (
            <div className="flex items-center gap-2 shrink-0">{actions}</div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
