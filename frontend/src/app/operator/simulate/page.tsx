/**
 * Simulation Page – /operator/simulate
 *
 * What-if scenario tool for operators to explore flood risk
 * under different weather conditions.
 */

import { SimulationPanel } from "@/features/simulation";

export default function SimulationPage() {
  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Flood Simulation</h1>
        <p className="text-muted-foreground">
          Explore what-if scenarios by adjusting weather parameters. Predictions
          are ephemeral and not stored.
        </p>
      </div>

      <SimulationPanel />
    </div>
  );
}
