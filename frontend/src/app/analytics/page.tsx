/**
 * Analytics Page - Landing-page-inspired overhaul
 *
 * Data visualization dashboard for LGU operators and admins.
 * Shows rainfall trends, risk distribution, alert frequency,
 * and model performance charts.
 */

import { motion, useInView } from "framer-motion";
import { BarChart3 } from "lucide-react";
import { useRef } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { fadeUp, staggerContainer } from "@/lib/motion";

import {
  AlertFrequency,
  RainfallTrend,
  RiskDistribution,
} from "@/features/dashboard/components/AnalyticsCharts";
import { ForecastPanel } from "@/features/dashboard/components/ForecastPanel";
import {
  AccuracyProgressionChart,
  ModelSummaryCards,
} from "@/features/dashboard/components/ModelManagement";

export default function AnalyticsPage() {
  const modelRef = useRef<HTMLDivElement>(null);
  const modelInView = useInView(modelRef, { once: true, amount: 0.1 });
  const chartsRef = useRef<HTMLDivElement>(null);
  const chartsInView = useInView(chartsRef, { once: true, amount: 0.05 });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <PageHeader
          icon={BarChart3}
          title="Analytics"
          subtitle="Weather trends, risk analysis, and model performance at a glance"
        />
      </div>

      {/* Model Summary Section */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={modelRef}>
          <SectionHeading
            label="Model Overview"
            title="AI Model Summary"
            subtitle="Key metrics for the current flood prediction model"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={modelInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <ModelSummaryCards />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Charts Section */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={chartsRef}>
          <SectionHeading
            label="Data Visualization"
            title="Trends & Distribution"
            subtitle="Explore rainfall patterns, risk levels, alert frequency, and forecast data"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={chartsInView ? "show" : undefined}
            className="grid gap-6 lg:grid-cols-2"
          >
            <motion.div variants={fadeUp}>
              <RainfallTrend />
            </motion.div>
            <motion.div variants={fadeUp}>
              <ForecastPanel hours={12} />
            </motion.div>
            <motion.div variants={fadeUp}>
              <RiskDistribution />
            </motion.div>
            <motion.div variants={fadeUp}>
              <AlertFrequency />
            </motion.div>
            <motion.div variants={fadeUp} className="lg:col-span-2">
              <AccuracyProgressionChart className="lg:col-span-2" />
            </motion.div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
