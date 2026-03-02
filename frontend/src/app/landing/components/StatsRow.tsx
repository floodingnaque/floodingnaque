/**
 * StatsRow Component
 *
 * Animated count-up statistics that trigger when scrolled into view.
 * Values are sourced from thesis data (MODEL_VERSIONS v6).
 */

import { useEffect, useRef, useState } from 'react';
import { motion, useInView } from 'framer-motion';

// ---------------------------------------------------------------------------
// Count-up hook
// ---------------------------------------------------------------------------

function useCountUp(target: number, duration = 2000, isInView: boolean, decimals = 0) {
  const [value, setValue] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    if (!isInView || started.current) return;
    started.current = true;

    const start = performance.now();
    const step = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(+(eased * target).toFixed(decimals));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [isInView, target, duration, decimals]);

  return value;
}

// ---------------------------------------------------------------------------
// Stat data
// ---------------------------------------------------------------------------

const STATS = [
  {
    target: 1182,
    suffix: '',
    label: 'Official Flood Records',
    source: 'Parañaque City DRRMO 2022–2025',
    decimals: 0,
  },
  {
    target: 96.75,
    suffix: '%',
    label: 'Model Accuracy',
    source: 'Random Forest v6',
    decimals: 2,
  },
  {
    target: 16,
    suffix: '',
    label: 'Barangays Monitored',
    source: 'All barangays of Parañaque',
    decimals: 0,
  },
  {
    target: 13698,
    suffix: '',
    label: 'Training Samples',
    source: 'Balanced flood/non-flood instances',
    decimals: 0,
  },
] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function StatsRow() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.3 });

  return (
    <section id="stats" className="py-16 sm:py-20 bg-muted/30">
      <div className="container mx-auto px-4" ref={ref}>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 sm:gap-12">
          {STATS.map((stat, i) => (
            <StatCard key={stat.label} stat={stat} index={i} isInView={isInView} />
          ))}
        </div>
      </div>
    </section>
  );
}

function StatCard({
  stat,
  index,
  isInView,
}: {
  stat: (typeof STATS)[number];
  index: number;
  isInView: boolean;
}) {
  const value = useCountUp(stat.target, 2000, isInView, stat.decimals);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={isInView ? { opacity: 1, y: 0 } : undefined}
      transition={{ delay: index * 0.15, duration: 0.5 }}
      className="text-center space-y-1"
    >
      <p className="text-4xl sm:text-5xl font-extrabold text-primary tabular-nums tracking-tight">
        {stat.decimals > 0
          ? value.toFixed(stat.decimals)
          : Math.round(value).toLocaleString()}
        {stat.suffix}
      </p>
      <p className="text-sm font-semibold text-foreground tracking-tight">{stat.label}</p>
      <p className="text-xs text-muted-foreground font-medium">{stat.source}</p>
    </motion.div>
  );
}

export default StatsRow;
