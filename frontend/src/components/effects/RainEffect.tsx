/**
 * RainEffect — Animated rain drop overlay.
 *
 * Reusable across pages for visual consistency.  Configurable density
 * and opacity so it can be prominent on the hero/login screens and
 * very subtle inside the authenticated layout.
 *
 * @example
 *   <RainEffect />                          // default (30 drops)
 *   <RainEffect density={15} opacity={0.06} />  // subtle mode
 */

import { useMemo } from 'react';
import { cn } from '@/lib/utils';

interface RainEffectProps {
  /** Number of rain drops to render (default: 30). */
  density?: number;
  /** Base opacity of each drop (0–1, default: 0.10). */
  opacity?: number;
  /** Extra Tailwind/CSS classes on the wrapper. */
  className?: string;
}

interface Drop {
  id: number;
  left: string;
  top: string;
  height: string;
  duration: string;
  delay: string;
}

/**
 * Generate stable rain drop configs so they don't re-randomise on
 * every render (would cause layout thrash).
 */
function generateDrops(count: number): Drop[] {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    left: `${(i * 37 + 13) % 100}%`,          // deterministic spread
    top: `-${(i * 23 + 7) % 20}%`,
    height: `${12 + ((i * 19 + 5) % 24)}px`,
    duration: `${0.8 + ((i * 13 + 3) % 12) / 10}s`,
    delay: `${((i * 11 + 2) % 20) / 10}s`,
  }));
}

export function RainEffect({ density = 30, opacity = 0.1, className }: RainEffectProps) {
  const drops = useMemo(() => generateDrops(density), [density]);

  return (
    <div
      className={cn('absolute inset-0 overflow-hidden pointer-events-none', className)}
      aria-hidden
    >
      {drops.map((d) => (
        <div
          key={d.id}
          className="absolute w-px rounded-full rain-drop"
          style={{
            left: d.left,
            top: d.top,
            height: d.height,
            backgroundColor: `rgba(255,255,255,${opacity})`,
            animationDuration: d.duration,
            animationDelay: d.delay,
          }}
        />
      ))}
    </div>
  );
}

export default RainEffect;
