/**
 * StatsRow Component
 *
 * Animated count-up statistics that trigger when scrolled into view.
 * Values are sourced from trained model v6 metadata.
 */

import { motion, useInView } from "framer-motion";
import { useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Count-up hook
// ---------------------------------------------------------------------------

function useCountUp(
  target: number,
  duration = 2000,
  isInView: boolean,
  decimals = 0,
) {
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
    target: 901,
    suffix: "",
    label: "Official Flood Records",
    source: "Parañaque City DRRMO 2022–2025",
    decimals: 0,
  },
  {
    target: 97.35,
    suffix: "%",
    label: "Model Accuracy",
    source: "Random Forest v6",
    decimals: 2,
  },
  {
    target: 16,
    suffix: "",
    label: "Barangays Monitored",
    source: "All barangays of Parañaque",
    decimals: 0,
  },
  {
    target: 6570,
    suffix: "",
    label: "Training Samples",
    source: "Balanced flood/non-flood instances",
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
      <div className="container px-4 mx-auto" ref={ref}>
        <div className="grid grid-cols-2 gap-8 lg:grid-cols-4 sm:gap-12">
          {STATS.map((stat, i) => (
            <StatCard
              key={stat.label}
              stat={stat}
              index={i}
              isInView={isInView}
            />
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
      className="space-y-1 text-center"
    >
      <p className="text-4xl font-extrabold tracking-tight sm:text-5xl text-primary tabular-nums">
        {stat.decimals > 0
          ? value.toFixed(stat.decimals)
          : Math.round(value).toLocaleString()}
        {stat.suffix}
      </p>
      <p className="text-sm font-semibold tracking-tight text-foreground">
        {stat.label}
      </p>
      <p className="text-xs font-medium text-muted-foreground">{stat.source}</p>
    </motion.div>
  );
}

export default StatsRow;
