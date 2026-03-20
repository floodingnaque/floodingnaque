/**
 * DualCTA Component
 *
 * Two-column call-to-action: one for Residents, one for LGU / DRRMO.
 * Small "System Admin" link beneath the LGU card.
 */

import { Button } from "@/components/ui/button";
import { useIsAuthenticated, useUser } from "@/state/stores";
import { motion, useInView } from "framer-motion";
import { Building2, ShieldCheck, Users } from "lucide-react";
import { useRef } from "react";
import { Link } from "react-router-dom";

export function DualCTA() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.25 });
  const isAuthenticated = useIsAuthenticated();
  const user = useUser();

  return (
    <section id="cta" className="py-20 sm:py-24 bg-background">
      <div className="container mx-auto px-4" ref={ref}>
        {/* Heading */}
        <div className="text-center mb-12">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-risk-safe mb-3">
            Get Started
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            Choose Your Dashboard
          </h2>
          <p className="mt-3 text-muted-foreground max-w-lg mx-auto leading-relaxed">
            Whether you're a resident checking your barangay or an LGU officer
            managing alerts - we've got you covered.
          </p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {/* Resident card */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={isInView ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.5 }}
            className="rounded-xl border border-risk-safe/30 bg-risk-safe/5 p-8 flex flex-col items-center text-center space-y-5"
          >
            <div className="h-16 w-16 rounded-full bg-risk-safe/15 flex items-center justify-center">
              <Users className="h-8 w-8 text-risk-safe" />
            </div>
            <h3 className="text-xl font-bold text-foreground">For Residents</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Monitor real-time flood risk levels across Paranaque City
              barangays, explore an interactive risk map, and receive timely
              early-warning notifications.
            </p>
            <Button
              asChild
              size="lg"
              className="bg-risk-safe hover:bg-risk-safe/90 text-white w-full mt-auto"
            >
              <Link
                to={
                  isAuthenticated && user?.role === "user"
                    ? "/resident"
                    : "/login"
                }
              >
                {isAuthenticated && user?.role === "user"
                  ? "Go to Dashboard"
                  : "Check My Barangay"}{" "}
                &rarr;
              </Link>
            </Button>
          </motion.div>

          {/* LGU / DRRMO card */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={isInView ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="rounded-xl border border-primary/30 bg-primary/5 p-8 flex flex-col items-center text-center space-y-5"
          >
            <div className="h-16 w-16 rounded-full bg-primary/15 flex items-center justify-center">
              <Building2 className="h-8 w-8 text-primary" />
            </div>
            <h3 className="text-xl font-bold text-foreground">
              For LGU / DRRMO
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Oversee flood operations from a centralized command dashboard,
              dispatch multi-channel alerts, generate compliance reports, and
              evaluate predictive models.
            </p>
            <Button
              asChild
              size="lg"
              className="bg-primary hover:bg-primary/90 text-white w-full mt-auto"
            >
              <Link
                to={
                  isAuthenticated && user?.role === "operator"
                    ? "/operator"
                    : "/login?role=lgu"
                }
              >
                {isAuthenticated && user?.role === "operator"
                  ? "Go to Dashboard"
                  : "LGU Dashboard"}{" "}
                &rarr;
              </Link>
            </Button>
          </motion.div>

          {/* Admin card */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={isInView ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="rounded-xl border border-risk-alert/30 bg-risk-alert/5 p-8 flex flex-col items-center text-center space-y-5"
          >
            <div className="h-16 w-16 rounded-full bg-risk-alert/15 flex items-center justify-center">
              <ShieldCheck className="h-8 w-8 text-risk-alert" />
            </div>
            <h3 className="text-xl font-bold text-foreground">System Admin</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Administer user roles and permissions, audit system activity logs,
              configure platform feature flags, and monitor infrastructure
              health in real time.
            </p>
            <Button
              asChild
              size="lg"
              className="bg-risk-alert hover:bg-risk-alert/90 text-white w-full mt-auto"
            >
              <Link
                to={
                  isAuthenticated && user?.role === "admin"
                    ? "/admin"
                    : "/login?role=admin"
                }
              >
                {isAuthenticated && user?.role === "admin"
                  ? "Go to Dashboard"
                  : "Admin Portal"}{" "}
                &rarr;
              </Link>
            </Button>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

export default DualCTA;
