/**
 * BarangayMapSection Component
 *
 * Embeds the existing BarangayRiskMap (zero props = static config risk)
 * plus a summary table listing all 16 barangays with population and
 * default risk level.
 */

import { Suspense, lazy, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { MapPin, Loader2 } from 'lucide-react';
import { BARANGAYS } from '@/config/paranaque';

// Lazy-load the heavy map component (Leaflet + tiles)
const BarangayRiskMap = lazy(() =>
  import('@/features/dashboard/components/BarangayRiskMap').then((m) => ({
    default: m.BarangayRiskMap,
  })),
);

const RISK_LABEL: Record<string, { text: string; className: string }> = {
  high: { text: 'High', className: 'text-risk-critical font-semibold' },
  moderate: { text: 'Moderate', className: 'text-risk-alert font-semibold' },
  low: { text: 'Low', className: 'text-risk-safe font-semibold' },
};

export function BarangayMapSection() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.1 });

  return (
    <section id="barangay-map" className="py-20 sm:py-24 bg-muted/30">
      <div className="container mx-auto px-4" ref={ref}>
        {/* Heading */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : undefined}
          transition={{ duration: 0.5 }}
          className="text-center mb-10"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-risk-safe mb-3">
            Barangay Coverage
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            All 16 Barangays at a Glance
          </h2>
          <p className="mt-3 text-muted-foreground max-w-xl mx-auto leading-relaxed">
            Each polygon on the map is coloured by its historical flood risk. Click any barangay for
            details, population, and evacuation centre.
          </p>
        </motion.div>

        {/* Map */}
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={isInView ? { opacity: 1, scale: 1 } : undefined}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="rounded-xl overflow-hidden shadow-lg border border-border/40"
        >
          <Suspense
            fallback={
              <div className="flex items-center justify-center h-125 bg-muted/30">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            }
          >
            <BarangayRiskMap height={500} />
          </Suspense>
        </motion.div>

        {/* Barangay summary table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : undefined}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="mt-10 max-w-4xl mx-auto"
        >
          <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <MapPin className="h-5 w-5 text-primary" />
            Barangay Summary
          </h3>

          <div className="overflow-x-auto rounded-lg border border-border/40 bg-background">
            <table className="w-full text-sm" aria-label="Barangay flood risk summary">
              <thead>
                <tr className="bg-muted/50 text-left">
                  <th scope="col" className="px-4 py-2.5 font-medium text-muted-foreground">Barangay</th>
                  <th scope="col" className="px-4 py-2.5 font-medium text-muted-foreground text-right">
                    Population
                  </th>
                  <th scope="col" className="px-4 py-2.5 font-medium text-muted-foreground text-center">
                    Flood Risk
                  </th>
                  <th scope="col" className="px-4 py-2.5 font-medium text-muted-foreground">
                    Evacuation Centre
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30">
                {BARANGAYS.map((b) => {
                  const risk = RISK_LABEL[b.floodRisk] ?? RISK_LABEL.low;
                  return (
                    <tr key={b.key} className="hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-2 font-medium text-foreground">{b.name}</td>
                      <td className="px-4 py-2 text-right text-muted-foreground tabular-nums">
                        {b.population.toLocaleString()}
                      </td>
                      <td className={`px-4 py-2 text-center ${risk.className}`}>{risk.text}</td>
                      <td className="px-4 py-2 text-muted-foreground text-xs">
                        {b.evacuationCenter}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

export default BarangayMapSection;
