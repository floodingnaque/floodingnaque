/**
 * Flood Map Page — Landing-page-inspired overhaul
 *
 * Full-screen barangay risk map with dark hero header,
 * animated sections, and emergency info panel.
 */

import { motion, useInView } from "framer-motion";
import { Map, WifiOff } from "lucide-react";
import { useRef, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
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
      {/* Header */}
      <div className="container mx-auto px-4 pt-6">
        <PageHeader
          icon={Map}
          title="Flood Map"
          subtitle="Interactive barangay flood risk visualization across all 16 barangays of Parañaque City"
        />
      </div>

      {/* Map Section */}
      <section className="py-10 bg-muted/30">
        <div className="container mx-auto px-4" ref={mapRef}>
          <SectionHeading
            label="Risk Visualization"
            title="Barangay Flood Risk Map"
            subtitle="Click any barangay to view detailed risk information, evacuation centers, and historical data."
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={mapInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <BarangayRiskMap prediction={prediction} height={600} />
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
          Live capacity updates unavailable — showing cached data
        </div>
      )}
    </div>
  );
}
