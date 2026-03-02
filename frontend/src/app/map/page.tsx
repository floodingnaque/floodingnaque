/**
 * Flood Map Page
 *
 * Full-screen barangay risk map for all roles.
 * Re-uses BarangayRiskMap component with live prediction data.
 */

import { useLivePrediction } from '@/features/flooding/hooks/useLivePrediction';
import { BarangayRiskMap } from '@/features/dashboard/components/BarangayRiskMap';
import { EmergencyInfoPanel } from '@/features/dashboard/components/EmergencyInfoPanel';

export default function MapPage() {
  const { data: prediction } = useLivePrediction();

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <BarangayRiskMap prediction={prediction} height={600} />
      <EmergencyInfoPanel filterHighRisk={false} />
    </div>
  );
}
