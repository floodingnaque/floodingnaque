/**
 * FeatureCards Component
 *
 * 3×2 grid showcasing the six main features of the Floodingnaque system.
 * Each card has an icon, bold title, and short description.
 */

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import {
  Map,
  Brain,
  Bell,
  Waves,
  History,
  FileSpreadsheet,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

const FEATURES = [
  {
    icon: Map,
    title: 'Barangay Risk Map',
    desc: 'Interactive Leaflet map with polygon overlays coloured by real-time risk level for all 16 barangays.',
  },
  {
    icon: Brain,
    title: 'AI-Powered Prediction',
    desc: 'Random Forest v6 model trained on 10 weather & tidal features with 96.75% accuracy on balanced test set.',
  },
  {
    icon: Bell,
    title: 'Instant Flood Alerts',
    desc: 'SSE push notifications and simulated SMS broadcasts provide immediate warnings when risk changes.',
  },
  {
    icon: Waves,
    title: 'Tidal Risk Monitoring',
    desc: 'Real-time tidal level indicators with configurable thresholds to flag dangerous storm surge conditions.',
  },
  {
    icon: History,
    title: '4-Year Flood History',
    desc: 'Explore 1,182 official flood records from 2022–2025 with filterable charts and statistical breakdowns.',
  },
  {
    icon: FileSpreadsheet,
    title: 'LGU Report Generator',
    desc: 'One-click DRRMO-formatted CSV & PDF export of flood events, sortable by barangay, date, and severity.',
  },
] as const;

const container = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.12, delayChildren: 0.1 },
  },
};

const cardVariant = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45 } },
};

export function FeatureCards() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.15 });

  return (
    <section id="features" className="py-20 sm:py-24 bg-muted/30">
      <div className="container mx-auto px-4" ref={ref}>
        {/* Heading */}
        <div className="text-center mb-14">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-risk-safe mb-3">
            Features
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            Everything You Need for Flood Preparedness
          </h2>
          <p className="mt-3 text-muted-foreground max-w-xl mx-auto leading-relaxed">
            Purpose-built for Parañaque City - from real-time maps to DRRMO compliance reports.
          </p>
        </div>

        {/* Card Grid */}
        <motion.div
          variants={container}
          initial="hidden"
          animate={isInView ? 'show' : undefined}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto"
        >
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <motion.div key={f.title} variants={cardVariant}>
                <Card className="h-full hover:shadow-md transition-all duration-300 border-border/50 hover:border-border">
                  <CardHeader className="space-y-3">
                    <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-base">{f.title}</CardTitle>
                    <CardDescription className="text-sm leading-relaxed">
                      {f.desc}
                    </CardDescription>
                  </CardHeader>
                </Card>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}

export default FeatureCards;
