/**
 * Flood Map Page - Landing-page-inspired overhaul
 *
 * Full-screen barangay risk map with dark hero header,
 * animated sections, and emergency info panel.
 */

import { motion, useInView } from "framer-motion";
import { Crosshair, Loader2, WifiOff } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

import { SectionHeading } from "@/components/layout/SectionHeading";
import { ReportFAB } from "@/features/community/components/ReportFAB";
import { ReportSubmitModal } from "@/features/community/components/ReportSubmitModal";
import { BarangayRiskMap } from "@/features/dashboard/components/BarangayRiskMap";
import { EmergencyInfoPanel } from "@/features/dashboard/components/EmergencyInfoPanel";
import { useCapacityStream } from "@/features/evacuation/hooks/useCapacityStream";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { fadeUp, staggerContainer } from "@/lib/motion";

export default function MapPage() {
  const { data: prediction } = useLivePrediction();
  const [reportOpen, setReportOpen] = useState(false);
  const [locating, setLocating] = useState(false);
  const [userLocation, setUserLocation] = useState<[number, number] | null>(
    null,
  );

  const handleLocate = useCallback(() => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation([pos.coords.latitude, pos.coords.longitude]);
        setLocating(false);
      },
      () => setLocating(false),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }, []);

  // Auto-detect user location on page load
  useEffect(() => {
    handleLocate();
  }, [handleLocate]);

  // Real-time capacity SSE stream
  const { isConnected: capacityConnected } = useCapacityStream({
    enabled: true,
  });

  const mapRef = useRef<HTMLDivElement>(null);
  const mapInView = useInView(mapRef, { once: true, amount: 0.1 });

  const infoRef = useRef<HTMLDivElement>(null);
  const infoInView = useInView(infoRef, { once: true, amount: 0.1 });

  return (
    <div className="min-h-screen bg-background">
      {/* Map Section */}
      <section className="py-10 bg-muted/30">
        <div className="container mx-auto px-4" ref={mapRef}>
          <SectionHeading
            label="Risk Visualization"
            title="Barangay Flood Risk Map"
            subtitle="Click any barangay to view detailed risk information, evacuation centers, and historical data."
          />
          <div className="flex justify-end mb-3">
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={handleLocate}
              disabled={locating}
            >
              {locating ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Crosshair className="h-3 w-3" />
              )}
              My Location
            </Button>
          </div>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={mapInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <BarangayRiskMap
                prediction={prediction}
                height={600}
                userLocation={userLocation}
              />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Emergency Info Section */}
      <section className="py-10 bg-background">
        <div className="container mx-auto px-4" ref={infoRef}>
          <SectionHeading
            label="Emergency Preparedness"
            title="Hotlines & Evacuation Centers"
            subtitle="Critical contacts and nearby evacuation centers for all barangays."
          />
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={infoInView ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.5 }}
          >
            <EmergencyInfoPanel filterHighRisk={false} />
          </motion.div>
        </div>
      </section>

      {/* Floating Report Button + Modal */}
      <ReportFAB onClick={() => setReportOpen(true)} />
      <ReportSubmitModal open={reportOpen} onOpenChange={setReportOpen} />

      {/* Offline capacity stream banner */}
      {!capacityConnected && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 rounded-full bg-risk-alert/15 px-4 py-1.5 text-xs text-risk-alert shadow-lg">
          <WifiOff className="h-3.5 w-3.5" />
          Live capacity updates unavailable - showing cached data
        </div>
      )}
    </div>
  );
}
