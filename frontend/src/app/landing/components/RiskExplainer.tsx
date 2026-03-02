/**
 * RiskExplainer Component
 *
 * Three-column visual explaining the SAFE / ALERT / CRITICAL risk levels
 * with matching dashboard risk colours.
 */

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { ShieldCheck, AlertTriangle, ShieldAlert } from 'lucide-react';

const LEVELS = [
  {
    label: 'SAFE',
    icon: ShieldCheck,
    color: 'text-risk-safe',
    bg: 'bg-risk-safe/10',
    border: 'border-risk-safe/30',
    dot: 'bg-risk-safe',
    threshold: '< 30 %',
    description:
      'Flood probability is low. Normal conditions - no action needed. The system continues to monitor all weather inputs.',
  },
  {
    label: 'ALERT',
    icon: AlertTriangle,
    color: 'text-risk-alert',
    bg: 'bg-risk-alert/10',
    border: 'border-risk-alert/30',
    dot: 'bg-risk-alert',
    threshold: '30 – 75 %',
    description:
      'Moderate flood probability detected. Residents in low-lying areas should monitor updates and prepare evacuation bags.',
  },
  {
    label: 'CRITICAL',
    icon: ShieldAlert,
    color: 'text-risk-critical',
    bg: 'bg-risk-critical/10',
    border: 'border-risk-critical/30',
    dot: 'bg-risk-critical',
    threshold: '≥ 75 %',
    description:
      'High flood probability. Immediate action recommended - follow DRRMO evacuation protocols and move to designated evacuation centres.',
  },
] as const;

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.15, delayChildren: 0.1 } },
};

const card = {
  hidden: { opacity: 0, scale: 0.95 },
  show: { opacity: 1, scale: 1, transition: { duration: 0.45 } },
};

export function RiskExplainer() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.2 });

  return (
    <section id="risk-levels" className="py-20 sm:py-24 bg-background">
      <div className="container mx-auto px-4" ref={ref}>
        {/* Heading */}
        <div className="text-center mb-14">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-risk-safe mb-3">
            Risk Levels
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            Understanding Flood Risk Levels
          </h2>
          <p className="mt-3 text-muted-foreground max-w-xl mx-auto leading-relaxed">
            Every prediction is reduced to one of three actionable levels - matching exactly what
            you see on the dashboard.
          </p>
        </div>

        {/* Cards */}
        <motion.div
          variants={container}
          initial="hidden"
          animate={isInView ? 'show' : undefined}
          className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto"
        >
          {LEVELS.map((l) => {
            const Icon = l.icon;
            return (
              <motion.div
                key={l.label}
                variants={card}
                className={`rounded-xl border ${l.border} ${l.bg} p-8 flex flex-col items-center text-center space-y-4`}
              >
                {/* Dot indicator */}
                <span className={`inline-block h-3 w-3 rounded-full ${l.dot}`} />

                {/* Icon */}
                <div className={`h-14 w-14 rounded-full ${l.bg} flex items-center justify-center`}>
                  <Icon className={`h-7 w-7 ${l.color}`} />
                </div>

                {/* Label & threshold */}
                <h3 className={`text-xl font-bold ${l.color}`}>{l.label}</h3>
                <p className="text-sm font-medium text-muted-foreground">
                  Probability {l.threshold}
                </p>

                {/* Description */}
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {l.description}
                </p>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}

export default RiskExplainer;
