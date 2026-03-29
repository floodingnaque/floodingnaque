/**
 * AuthPageLayout - Shared layout wrapper for all auth pages
 *
 * Provides consistent branding, rain effect background, navigation,
 * and city status badge across Login, Register, and Forgot Password pages.
 */

import { RainEffect } from "@/components/effects/RainEffect";
import { FloodIcon } from "@/components/icons/FloodIcon";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { CityStatusBadge } from "./CityStatusBadge";

interface AuthPageLayoutProps {
  children: React.ReactNode;
  /** Link target for the back button */
  backTo?: string;
  /** Back button label */
  backLabel?: string;
  /** Whether to show the left branding panel (desktop only) */
  showBrandingPanel?: boolean;
  /** Additional className for the content container */
  className?: string;
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.15 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: "easeOut" as const },
  },
} as const;

function BrandingPanel() {
  return (
    <motion.div
      className="hidden lg:flex flex-col justify-center p-12 text-white space-y-8 max-w-lg"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {/* Logo */}
      <motion.div variants={itemVariants} className="flex items-center gap-3">
        <div className="flex items-center justify-center h-14 w-14 rounded-xl bg-white/15 backdrop-blur-sm ring-2 ring-white/10">
          <FloodIcon className="h-7 w-7 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Floodingnaque</h1>
          <p className="text-xs text-white/50">Parañaque City DRRMO</p>
        </div>
      </motion.div>

      {/* Status badge */}
      <motion.div variants={itemVariants}>
        <CityStatusBadge className="border-white/20 bg-white/10 text-white" />
      </motion.div>

      {/* Tagline */}
      <motion.div variants={itemVariants} className="space-y-3">
        <h2 className="text-3xl font-bold leading-tight">
          Real-time flood risk monitoring for all 16 barangays of Parañaque City
        </h2>
        <p className="text-sm text-white/60 leading-relaxed">
          AI-powered flood prediction system built for the City Disaster Risk
          Reduction and Management Office. Protecting communities through early
          warning and coordinated emergency response.
        </p>
      </motion.div>

      {/* Stats */}
      <motion.div variants={itemVariants} className="flex gap-8">
        <div>
          <p className="text-3xl font-bold">16</p>
          <p className="text-xs text-white/50 mt-0.5">Barangays Monitored</p>
        </div>
        <div className="w-px bg-white/15" />
        <div>
          <p className="text-3xl font-bold">96.75%</p>
          <p className="text-xs text-white/50 mt-0.5">Model Accuracy</p>
        </div>
        <div className="w-px bg-white/15" />
        <div>
          <p className="text-3xl font-bold">3,700+</p>
          <p className="text-xs text-white/50 mt-0.5">Flood Records</p>
        </div>
      </motion.div>

      {/* Footer */}
      <motion.p variants={itemVariants} className="text-xs text-white/30">
        &copy; {new Date().getFullYear()} Floodingnaque. Developed for academic
        research and public safety.
      </motion.p>
    </motion.div>
  );
}

export function AuthPageLayout({
  children,
  backTo = "/",
  backLabel = "Back to home",
  showBrandingPanel = false,
  className,
}: AuthPageLayoutProps) {
  return (
    <div className="relative min-h-screen flex bg-primary overflow-x-hidden overflow-y-auto">
      {/* Rain + gradient overlay */}
      <RainEffect />
      <div className="absolute inset-0 bg-linear-to-b from-black/20 via-transparent to-black/30 pointer-events-none" />

      {/* Decorative glow orbs */}
      <div className="pointer-events-none absolute -top-32 -left-32 h-64 w-64 rounded-full bg-white/5 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -right-24 h-48 w-48 rounded-full bg-white/5 blur-3xl" />

      {/* Back navigation */}
      <motion.div
        initial={{ opacity: 0, x: -12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="absolute top-6 left-6 z-20"
      >
        <Link
          to={backTo}
          className="inline-flex items-center gap-1.5 text-sm text-white/60 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {backLabel}
        </Link>
      </motion.div>

      {/* Left branding panel - desktop only */}
      {showBrandingPanel && (
        <div className="relative z-10 hidden lg:flex lg:w-5/12 xl:w-1/2 items-center justify-center">
          <BrandingPanel />
        </div>
      )}

      {/* Right content panel */}
      <div
        className={cn(
          "relative z-10 flex flex-1 items-start sm:items-center justify-center p-4 pt-16 sm:p-6 sm:pt-6 min-h-screen",
          showBrandingPanel && "lg:w-7/12 xl:w-1/2",
          className,
        )}
      >
        <div
          className={cn("w-full", showBrandingPanel ? "max-w-lg" : "max-w-md")}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
