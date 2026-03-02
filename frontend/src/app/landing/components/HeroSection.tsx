/**
 * HeroSection Component
 *
 * Full-width navy hero with live risk badge, headline, subheadline,
 * and a streamlined CTA that scrolls to the "Get Started" section.
 * Redundant Sign In / LGU buttons removed — DualCTA handles role routing.
 */

import { motion } from 'framer-motion';
import { Droplets, ShieldCheck, AlertTriangle, ShieldAlert, ArrowDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { useLivePrediction } from '@/features/flooding/hooks/useLivePrediction';
import type { RiskLevel } from '@/types';

// ---------------------------------------------------------------------------
// Risk badge config (mirrors dashboard RISK_THEME)
// ---------------------------------------------------------------------------

const RISK_CFG: Record<RiskLevel, { label: string; bg: string; icon: typeof ShieldCheck }> = {
  0: { label: 'SAFE', bg: 'bg-risk-safe', icon: ShieldCheck },
  1: { label: 'ALERT', bg: 'bg-risk-alert', icon: AlertTriangle },
  2: { label: 'CRITICAL', bg: 'bg-risk-critical', icon: ShieldAlert },
};

// ---------------------------------------------------------------------------
// Animated rain drops (decorative)
// ---------------------------------------------------------------------------

function RainEffect() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden>
      {Array.from({ length: 30 }).map((_, i) => (
        <div
          key={i}
          className="absolute w-px bg-white/10 rounded-full"
          style={{
            left: `${Math.random() * 100}%`,
            top: `-${Math.random() * 20}%`,
            height: `${12 + Math.random() * 24}px`,
            animationName: 'rain-fall',
            animationDuration: `${0.8 + Math.random() * 1.2}s`,
            animationDelay: `${Math.random() * 2}s`,
            animationIterationCount: 'infinite',
            animationTimingFunction: 'linear',
          }}
        />
      ))}
      <style>{`
        @keyframes rain-fall {
          0%   { transform: translateY(-100%); opacity: 0; }
          10%  { opacity: 1; }
          90%  { opacity: 1; }
          100% { transform: translateY(calc(100vh + 100%)); opacity: 0; }
        }
      `}</style>
    </div>
  );
}

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

      <div className="relative z-10 container mx-auto px-4 py-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="max-w-3xl mx-auto space-y-8"
        >
          {/* Logo */}
          <div className="flex flex-col items-center gap-3">
            <div className="flex items-center justify-center h-20 w-20 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/10">
              <Droplets className="h-10 w-10 text-white" />
            </div>
            <span className="text-xs font-semibold tracking-[0.35em] uppercase text-white/50">
              Floodingnaque
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white leading-[1.08]">
            Real-Time Flood Detection{' '}
            <span className="text-risk-safe">for Parañaque City</span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg sm:text-xl text-white/75 max-w-2xl mx-auto leading-relaxed font-light">
            Machine learning-powered flood predictions for all 16 barangays, using live
            weather data, tidal readings, and 4 years of official DRRMO flood records.
          </p>

          {/* Live risk badge */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.5, type: 'spring' }}
            className="flex justify-center"
          >
            {isLoading ? (
              <Skeleton className="h-12 w-48 rounded-full bg-white/20" />
            ) : risk ? (
              <Badge
                className={cn(
                  'text-lg px-6 py-2.5 font-bold gap-2 shadow-lg animate-pulse',
                  risk.bg,
                  prediction?.risk_level === 1 ? 'text-black' : 'text-white',
                )}
              >
                <RiskIcon className="h-5 w-5" />
                Current Status: {risk.label}
              </Badge>
            ) : (
              <Badge className="text-lg px-6 py-2.5 font-bold bg-white/20 text-white">
                Connecting to sensors…
              </Badge>
            )}
          </motion.div>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center pt-2">
            <Button
              size="lg"
              onClick={() => document.getElementById('cta')?.scrollIntoView({ behavior: 'smooth' })}
              className="bg-risk-safe hover:bg-risk-safe/90 text-white text-base px-8 h-12 shadow-lg font-semibold"
            >
              Explore the System
            </Button>
            <Button
              size="lg"
              onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
              className="bg-white/10 border border-white/25 text-white hover:bg-white/20 text-base px-8 h-12 backdrop-blur-sm font-medium"
            >
              Learn How It Works
            </Button>
          </div>

          {/* Trust line */}
          <p className="text-sm text-white/50 pt-4">
            Trained on <strong className="text-white/70">1,182</strong> official flood records
            {' · '}
            <strong className="text-white/70">13,698</strong> training samples
            {' · '}
            <strong className="text-white/70">96.75%</strong> model accuracy
            {' · '}
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
              onClick={() => document.getElementById('live-status')?.scrollIntoView({ behavior: 'smooth' })}
              className="text-white/30 hover:text-white/60 transition-colors"
              aria-label="Scroll down"
            >
              <ArrowDown className="h-5 w-5 animate-bounce" />
            </button>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

export default HeroSection;
