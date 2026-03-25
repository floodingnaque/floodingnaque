/**
 * HeroSection Component
 *
 * Full-width navy hero with live risk badge, headline, subheadline,
 * and a streamlined CTA that scrolls to the "Get Started" section.
 * Redundant Sign In / LGU buttons removed - DualCTA handles role routing.
 */

import { FloodIcon } from "@/components/icons/FloodIcon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { cn } from "@/lib/utils";
import type { RiskLevel } from "@/types";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowDown,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Risk badge config (mirrors dashboard RISK_THEME)
// ---------------------------------------------------------------------------

const RISK_CFG: Record<
  RiskLevel,
  { label: string; bg: string; icon: typeof ShieldCheck }
> = {
  0: { label: "SAFE", bg: "bg-risk-safe", icon: ShieldCheck },
  1: { label: "ALERT", bg: "bg-risk-alert", icon: AlertTriangle },
  2: { label: "CRITICAL", bg: "bg-risk-critical", icon: ShieldAlert },
};

// ---------------------------------------------------------------------------
// Rain effect (shared component)
// ---------------------------------------------------------------------------

import { RainEffect } from "@/components/effects/RainEffect";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function HeroSection() {
  const { data: prediction, isLoading } = useLivePrediction();

  const risk = prediction ? RISK_CFG[prediction.risk_level] : null;
  const RiskIcon = risk?.icon ?? ShieldCheck;

  return (
    <section
      id="hero"
      className="relative min-h-[90vh] flex items-center justify-center bg-primary overflow-hidden"
    >
      <RainEffect />

      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-linear-to-b from-black/20 via-transparent to-black/30" />

      <div className="container relative z-10 px-4 py-24 mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="max-w-3xl mx-auto space-y-8"
        >
          {/* Logo */}
          <div className="flex flex-col items-center gap-3">
            <div className="flex items-center justify-center w-20 h-20 border rounded-2xl bg-white/10 backdrop-blur-sm border-white/10">
              <FloodIcon className="w-10 h-10 text-white" />
            </div>
            <span className="text-xs font-semibold tracking-[0.35em] uppercase text-white/50">
              Floodingnaque
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white leading-[1.08]">
            Real-Time Flood Detection{" "}
            <span className="text-risk-safe">for Parañaque City</span>
          </h1>

          {/* Subheadline */}
          <p className="max-w-2xl mx-auto text-lg font-light leading-relaxed sm:text-xl text-white/75">
            Random Forest Algorihm powered flood predictions for all 16
            barangays, using historical weather data, tidal readings, 5 years of
            PAGASA Stations, and 4 years of official DRRMO flood records.
          </p>

          {/* Live risk badge */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.5, type: "spring" }}
            className="flex justify-center"
          >
            {isLoading ? (
              <Skeleton className="w-48 h-12 rounded-full bg-white/20" />
            ) : risk ? (
              <Badge
                className={cn(
                  "text-lg px-6 py-2.5 font-bold gap-2 shadow-lg animate-pulse",
                  risk.bg,
                  prediction?.risk_level === 1 ? "text-black" : "text-white",
                )}
              >
                <RiskIcon className="w-5 h-5" />
                Current Status: {risk.label}
              </Badge>
            ) : (
              <Badge className="text-lg px-6 py-2.5 font-bold bg-white/20 text-white">
                Connecting to sensors…
              </Badge>
            )}
          </motion.div>

          {/* CTAs */}
          <div className="flex flex-col justify-center gap-4 pt-2 sm:flex-row">
            <Button
              size="lg"
              onClick={() =>
                document
                  .getElementById("cta")
                  ?.scrollIntoView({ behavior: "smooth" })
              }
              className="h-12 px-8 text-base font-semibold text-white shadow-lg bg-risk-safe hover:bg-risk-safe/90"
            >
              Explore the System
            </Button>
            <Button
              size="lg"
              onClick={() =>
                document
                  .getElementById("how-it-works")
                  ?.scrollIntoView({ behavior: "smooth" })
              }
              className="h-12 px-8 text-base font-medium text-white border bg-white/10 border-white/25 hover:bg-white/20 backdrop-blur-sm"
            >
              Learn How It Works
            </Button>
          </div>

          {/* Trust line */}
          <p className="pt-4 text-sm text-white/50">
            Trained on <strong className="text-white/70">901</strong> official
            flood records
            {" · "}
            <strong className="text-white/70">6,570</strong> training samples
            {" · "}
            <strong className="text-white/70">97.35%</strong> model accuracy
            {" · "}
            Parañaque City DRRMO data
          </p>

          {/* Scroll indicator */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5, duration: 0.8 }}
            className="flex justify-center pt-4"
          >
            <button
              onClick={() =>
                document
                  .getElementById("live-status")
                  ?.scrollIntoView({ behavior: "smooth" })
              }
              className="transition-colors text-white/30 hover:text-white/60"
              aria-label="Scroll down"
            >
              <ArrowDown className="w-5 h-5 animate-bounce" />
            </button>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

export default HeroSection;
