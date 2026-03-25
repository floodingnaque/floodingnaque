/**
 * Resident — Evacuation Plan Page
 *
 * Personalized plan based on household profile data,
 * with embedded map placeholder, step-by-step guide,
 * and household-specific checklists.
 */

import { AlertTriangle, CheckCircle, Route, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FloodMap } from "@/features/map";
import { useHouseholdProfile } from "@/features/resident";

export default function ResidentPlanPage() {
  const { data: household, isLoading } = useHouseholdProfile();

  const vulnerabilities: string[] = [];
  const extraSteps: string[] = [];
  if (household) {
    if (household.is_senior_citizen || household.senior_count > 0) {
      vulnerabilities.push("Senior citizen (60+)");
      extraSteps.push(
        "Assign a family member to assist the senior during evacuation.",
      );
    }
    if (household.children_count > 0) {
      vulnerabilities.push("Children under 5");
      extraSteps.push(
        "Pack extra diapers, formula, and a carrier for young children.",
      );
    }
    if (household.is_pwd || household.pwd_count > 0) {
      vulnerabilities.push("Person with disability (PWD)");
      extraSteps.push(
        "Bring mobility aids. Notify the evacuation center for assistance.",
      );
    }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Route className="h-5 w-5 text-primary" />
          Plano sa Paglikas / My Evacuation Plan
        </h2>
        <p className="text-sm text-muted-foreground">
          Plan your route to the nearest evacuation center
        </p>
      </div>

      {/* ── Map Placeholder ───────────────────────────────────────── */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <FloodMap height={350} />
        </CardContent>
      </Card>

      {/* ── Step-by-step Plan ─────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Mga Hakbang / Steps</CardTitle>
          <CardDescription>
            Follow this plan when an evacuation alert is issued
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            {
              step: 1,
              en: "Know Your Meeting Point",
              fil: "Alamin ang meeting point ng pamilya",
              desc: "Agree with your household on a meeting point outside your home in case you get separated.",
            },
            {
              step: 2,
              en: "Grab Your Go-Bag",
              fil: "Kunin ang go-bag",
              desc: "Bring documents, medicine, water, cash, and a charged phone.",
            },
            {
              step: 3,
              en: "Turn Off Utilities",
              fil: "Patayin ang kuryente at gas",
              desc: "Switch off electricity at the main breaker and close gas valves.",
            },
            {
              step: 4,
              en: "Follow Your Route",
              fil: "Sundin ang ruta ng paglikas",
              desc: "Take the shortest safe route to the nearest open evacuation center. Avoid flood-prone streets.",
            },
            {
              step: 5,
              en: "Register at the Center",
              fil: "Magpa-rehistro sa evacuation center",
              desc: "Sign in upon arrival so officials can account for everyone.",
            },
          ].map((s) => (
            <div key={s.step} className="p-3 rounded-lg bg-muted/50">
              <div className="flex items-start gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary text-sm font-bold shrink-0">
                  {s.step}
                </span>
                <div>
                  <p className="font-medium text-foreground text-sm">
                    {s.fil} / {s.en}
                  </p>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    {s.desc}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* ── Household-specific reminders ───────────────────────────── */}
      {isLoading ? (
        <Skeleton className="h-32 rounded-xl" />
      ) : vulnerabilities.length > 0 ? (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Users className="h-4 w-4 text-primary" />
              Household-Specific Reminders
            </CardTitle>
            <CardDescription>Based on your household profile</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {vulnerabilities.map((v, i) => (
              <div key={i} className="space-y-1">
                <div className="flex items-center gap-2 text-sm">
                  <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                  <span className="font-medium">{v}</span>
                </div>
                {extraSteps[i] && (
                  <p className="text-sm text-muted-foreground pl-6">
                    {extraSteps[i]}
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            <Users className="h-8 w-8 mx-auto mb-2 opacity-40" />
            <p className="text-sm font-medium mb-1">
              Complete your household profile
            </p>
            <p className="text-xs">
              Get personalized evacuation reminders for your family
            </p>
            <Button asChild variant="outline" size="sm" className="mt-3">
              <Link to="/resident/profile/household">Complete Profile</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ── Practice Reminder ─────────────────────────────────────── */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-primary/5 border border-primary/20">
        <CheckCircle className="h-5 w-5 text-primary mt-0.5 shrink-0" />
        <p className="text-sm">
          <span className="font-medium">Pro Tip:</span> Walk your evacuation
          route with your family so everyone knows the way, even in the dark or
          during heavy rain.
        </p>
      </div>
    </div>
  );
}
