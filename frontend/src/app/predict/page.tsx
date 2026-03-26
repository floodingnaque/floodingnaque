/**
 * Prediction Page - Landing-page-inspired overhaul
 *
 * Main page for flood risk prediction functionality.
 * Dark hero header, animated sections, offline-aware.
 */

import { motion, useInView } from "framer-motion";
import { CloudRain, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { StaleDataBanner } from "@/components/feedback/StaleDataBanner";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { PredictionForm } from "@/features/flooding/components/PredictionForm";
import { PredictionResult } from "@/features/flooding/components/PredictionResult";
import { useNetworkStatus } from "@/hooks/useNetworkStatus";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { getCachedPredictions } from "@/lib/offlineCache";
import type { PredictionResponse } from "@/types";

export default function PredictPage() {
  const [predictionResult, setPredictionResult] =
    useState<PredictionResponse | null>(null);
  const [offlineCachedAt, setOfflineCachedAt] = useState<string | null>(null);
  const { isOnline } = useNetworkStatus();

  const contentRef = useRef<HTMLDivElement>(null);
  const contentInView = useInView(contentRef, { once: true, amount: 0.1 });

  // Derive the displayed offline cache timestamp: clear it when back online
  const displayedCachedAt = isOnline ? null : offlineCachedAt;

  useEffect(() => {
    if (!isOnline && !predictionResult) {
      getCachedPredictions(1).then((cached) => {
        if (cached.length > 0 && cached[0]) {
          setPredictionResult(cached[0].data);
          setOfflineCachedAt(cached[0].cachedAt);
        }
      });
    }
  }, [isOnline, predictionResult]);

  const handlePredictionSuccess = (result: PredictionResponse) => {
    setPredictionResult(result);
  };

  const handleReset = () => {
    setPredictionResult(null);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="container mx-auto px-4 pt-4 sm:pt-6">
        <PageHeader
          icon={predictionResult ? ShieldAlert : CloudRain}
          title="Flood Risk Prediction"
          subtitle="Enter current weather conditions to assess flood risk. Our Random Forest model analyzes multiple factors for accurate predictions."
        />
      </div>

      {/* Main Content */}
      <section className="py-6 sm:py-10 bg-muted/30">
        <div className="container max-w-4xl mx-auto px-4" ref={contentRef}>
          <SectionHeading
            label={predictionResult ? "Assessment Result" : "Input Parameters"}
            title={
              predictionResult
                ? "Your Flood Risk Assessment"
                : "Weather Conditions Form"
            }
            subtitle={
              predictionResult
                ? "View your flood risk assessment below. You can make another prediction or view your prediction history."
                : "Provide current or forecasted weather data to generate a flood risk prediction for Parañaque City."
            }
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={contentInView ? "show" : undefined}
          >
            {displayedCachedAt && predictionResult && (
              <motion.div variants={fadeUp} className="mb-4">
                <StaleDataBanner cachedAt={displayedCachedAt} />
              </motion.div>
            )}

            <motion.div variants={fadeUp}>
              {predictionResult ? (
                <PredictionResult
                  result={predictionResult}
                  onReset={handleReset}
                />
              ) : (
                <PredictionForm onSuccess={handlePredictionSuccess} />
              )}
            </motion.div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
