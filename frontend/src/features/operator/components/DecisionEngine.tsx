/**
 * Decision Engine - Operator Decision Support Checklist
 *
 * Risk-level-aware action checklist for DRRMO field staff.
 * Displays recommended actions based on current flood risk level,
 * with progress tracking for situational accountability.
 */

import { cn } from "@/lib/utils";
import { CheckCircle2, Circle } from "lucide-react";
import { useState } from "react";

const ACTIONS_BY_RISK: Record<0 | 1 | 2, { id: number; action: string }[]> = {
  0: [
    { id: 1, action: "Confirm normal operations status with DRRMO chief" },
    { id: 2, action: "Verify all weather monitoring stations are online" },
    { id: 3, action: "Review 24-hour weather forecast" },
  ],
  1: [
    { id: 1, action: "Issue early warning to flood-prone barangays" },
    { id: 2, action: "Activate standby status for rescue teams" },
    { id: 3, action: "Coordinate pre-positioning of equipment" },
    { id: 4, action: "Monitor PAGASA weather bulletins every 30 minutes" },
  ],
  2: [
    {
      id: 1,
      action: "Issue mandatory evacuation order via citywide broadcast",
    },
    {
      id: 2,
      action: "Activate evacuation centers - notify barangay captains",
    },
    { id: 3, action: "Deploy rescue teams to high-risk barangays" },
    {
      id: 4,
      action: "Coordinate with PNP and Bureau of Fire for assistance",
    },
    {
      id: 5,
      action: "Notify NDRRMC and request additional resources if needed",
    },
  ],
};

const RISK_LABELS: Record<0 | 1 | 2, string> = {
  0: "SAFE",
  1: "ALERT",
  2: "CRITICAL",
};
const RISK_COLORS: Record<0 | 1 | 2, string> = {
  0: "text-green-600 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-950/30 dark:border-green-800",
  1: "text-amber-600 bg-amber-50 border-amber-200 dark:text-amber-400 dark:bg-amber-950/30 dark:border-amber-800",
  2: "text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-950/30 dark:border-red-800",
};

interface DecisionEngineProps {
  riskLevel: 0 | 1 | 2;
}

export function DecisionEngine({ riskLevel }: DecisionEngineProps) {
  const [completed, setCompleted] = useState<Set<number>>(new Set());

  const actions = ACTIONS_BY_RISK[riskLevel] ?? ACTIONS_BY_RISK[0];
  const completedCount = completed.size;
  const totalCount = actions.length;
  const progressPct =
    totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const toggleAction = (id: number) => {
    setCompleted((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div
      className={cn("rounded-xl border p-4 space-y-4", RISK_COLORS[riskLevel])}
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">Decision Support</h3>
          <p className="text-xs opacity-70 mt-0.5">
            Recommended actions for {RISK_LABELS[riskLevel]} status
          </p>
        </div>
        <div className="text-right">
          <p className="text-lg font-bold">{progressPct}%</p>
          <p className="text-xs opacity-70">complete</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-current/20 rounded-full overflow-hidden">
        <div
          className="h-full bg-current rounded-full transition-all duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Action checklist */}
      <div className="space-y-2">
        {actions.map(({ id, action }) => {
          const done = completed.has(id);
          return (
            <button
              key={id}
              onClick={() => toggleAction(id)}
              className={cn(
                "w-full flex items-start gap-2.5 text-left p-2",
                "rounded-lg transition-colors hover:bg-current/5",
              )}
            >
              {done ? (
                <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
              ) : (
                <Circle className="h-4 w-4 mt-0.5 shrink-0 opacity-40" />
              )}
              <span
                className={cn(
                  "text-xs leading-relaxed",
                  done && "line-through opacity-50",
                )}
              >
                {action}
              </span>
            </button>
          );
        })}
      </div>

      {completedCount > 0 && completedCount === totalCount && (
        <p className="text-xs text-center font-medium py-1">
          All actions completed
        </p>
      )}
    </div>
  );
}
