/**
 * FeatureCards Component
 *
 * 3×2 grid showcasing the six main features of the Floodingnaque system.
 * Each card has an icon, bold title, and short description.
 */

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { motion, useInView } from "framer-motion";
import {
  Bell,
  Brain,
  FileSpreadsheet,
  History,
  Map,
  Waves,
} from "lucide-react";
import { useRef } from "react";

const FEATURES = [
  {
    icon: Map,
    title: "Barangay Risk Map",
    desc: "Interactive Leaflet map with polygon overlays coloured by real-time risk level for all 16 barangays.",
  },
  {
    icon: Brain,
    title: "AI-Powered Prediction",
    desc: "Random Forest v6 model trained on 10 weather & tidal features with 96.75% accuracy on balanced test set.",
  },
  {
    icon: Bell,
    title: "Instant Flood Alerts",
    desc: "SSE push notifications and simulated SMS broadcasts provide immediate warnings when risk changes.",
  },
  {
    icon: Waves,
    title: "Tidal Risk Monitoring",
    desc: "Real-time tidal level indicators with configurable thresholds to flag dangerous storm surge conditions.",
  },
  {
    icon: History,
    title: "4-Year Flood History",
    desc: "Explore 901 official flood records from 2022–2025 with filterable charts and statistical breakdowns.",
  },
  {
    icon: FileSpreadsheet,
    title: "LGU Report Generator",
    desc: "One-click DRRMO-formatted CSV & PDF export of flood events, sortable by barangay, date, and severity.",
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
      <div className="container px-4 mx-auto" ref={ref}>
        {/* Heading */}
        <div className="text-center mb-14">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-risk-safe mb-3">
            Features
          </p>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl text-foreground">
            Everything You Need for Flood Preparedness
          </h2>
          <p className="max-w-xl mx-auto mt-3 leading-relaxed text-muted-foreground">
            Purpose-built for Parañaque City - from real-time maps to DRRMO
            compliance reports.
          </p>
        </div>

        {/* Card Grid */}
        <motion.div
          variants={container}
          initial="hidden"
          animate={isInView ? "show" : undefined}
          className="grid max-w-5xl grid-cols-1 gap-6 mx-auto sm:grid-cols-2 lg:grid-cols-3"
        >
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <motion.div key={f.title} variants={cardVariant}>
                <Card className="h-full transition-all duration-300 hover:shadow-md border-border/50 hover:border-border">
                  <CardHeader className="space-y-3">
                    <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-primary/10">
                      <Icon className="w-6 h-6 text-primary" />
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
