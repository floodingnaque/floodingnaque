/**
 * Landing Page Navbar
 *
 * Sticky navbar with transparent → solid transition, active section
 * tracking, professional typography, and streamlined CTAs.
 */

import { FloodIcon } from "@/components/icons/FloodIcon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useIsAuthenticated, useUser } from "@/state/stores";
import type { UserRole } from "@/types";
import { ChevronRight, LayoutDashboard, Menu, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

// ---------------------------------------------------------------------------
// Anchor-scroll helper
// ---------------------------------------------------------------------------

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
}

const NAV_LINKS = [
  { label: "Status", target: "live-status", group: "info" },
  { label: "How It Works", target: "how-it-works", group: "info" },
  { label: "Features", target: "features", group: "product" },
  { label: "Barangays", target: "barangay-map", group: "product" },
  { label: "About", target: "footer", group: "other" },
] as const;

// ---------------------------------------------------------------------------
// Role → dashboard route mapping
// ---------------------------------------------------------------------------

const DASHBOARD_ROUTES: Record<UserRole, { path: string; label: string }> = {
  admin: { path: "/admin", label: "Admin Dashboard" },
  operator: { path: "/operator", label: "Operator Dashboard" },
  user: { path: "/resident", label: "My Dashboard" },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<string>("");
  const observerRef = useRef<IntersectionObserver | null>(null);
  const isAuthenticated = useIsAuthenticated();
  const user = useUser();

  // Hero visibility → transparent/solid background
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setScrolled(!entry?.isIntersecting),
      { threshold: 0.1 },
    );
    const hero = document.getElementById("hero");
    if (hero) observer.observe(hero);
    return () => observer.disconnect();
  }, []);

  // Active section tracking via IntersectionObserver
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        }
      },
      { rootMargin: "-30% 0px -60% 0px", threshold: 0 },
    );

    const targets = NAV_LINKS.map((l) =>
      document.getElementById(l.target),
    ).filter((el): el is HTMLElement => el !== null);
    targets.forEach((el) => observerRef.current?.observe(el));

    return () => observerRef.current?.disconnect();
  }, []);

  const handleNav = useCallback((target: string) => {
    scrollTo(target);
    setMobileOpen(false);
  }, []);

  return (
    <nav
      className={cn(
        "fixed top-0 inset-x-0 z-50 transition-all duration-300",
        scrolled
          ? "bg-background/95 backdrop-blur-md shadow-sm border-b border-border/50"
          : "bg-transparent",
      )}
    >
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        {/* Logo */}
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="flex items-center gap-2.5 group"
        >
          <div
            className={cn(
              "flex items-center justify-center h-9 w-9 rounded-lg transition-colors",
              scrolled ? "bg-primary/10" : "bg-white/15",
            )}
          >
            <FloodIcon
              className={cn(
                "h-5 w-5 transition-colors",
                scrolled ? "text-primary" : "text-white",
              )}
            />
          </div>
          <span
            className={cn(
              "text-lg font-bold tracking-tight transition-colors",
              scrolled ? "text-foreground" : "text-white",
            )}
          >
            Floodingnaque
          </span>
        </button>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-0.5">
          {NAV_LINKS.map((link, idx) => {
            const isActive = activeSection === link.target;
            const prevGroup = idx > 0 ? NAV_LINKS[idx - 1]?.group : link.group;
            const showDivider = idx > 0 && prevGroup !== link.group;
            return (
              <div key={link.target} className="flex items-center">
                {showDivider && (
                  <span
                    className={cn(
                      "mx-1.5 h-4 w-px rounded-full",
                      scrolled ? "bg-border" : "bg-white/20",
                    )}
                  />
                )}
                <button
                  onClick={() => handleNav(link.target)}
                  className={cn(
                    "relative px-3 py-2 text-sm font-medium rounded-md transition-colors",
                    scrolled
                      ? isActive
                        ? "text-primary bg-primary/5"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                      : isActive
                        ? "text-white bg-white/15"
                        : "text-white/70 hover:text-white hover:bg-white/10",
                  )}
                >
                  {link.label}
                  {isActive && (
                    <span
                      className={cn(
                        "absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 w-5 rounded-full",
                        scrolled ? "bg-primary" : "bg-white",
                      )}
                    />
                  )}
                </button>
              </div>
            );
          })}
        </div>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center gap-3">
          {isAuthenticated && user ? (
            <Button
              size="sm"
              asChild
              className={cn(
                "h-9 px-5 font-medium transition-all",
                scrolled
                  ? "bg-primary hover:bg-primary/90 text-white shadow-sm"
                  : "bg-white/15 text-white border border-white/25 hover:bg-white/25 backdrop-blur-sm",
              )}
            >
              <Link
                to={DASHBOARD_ROUTES[user.role].path}
                className="inline-flex items-center gap-1.5"
              >
                <LayoutDashboard className="h-3.5 w-3.5" />
                {DASHBOARD_ROUTES[user.role].label}
              </Link>
            </Button>
          ) : (
            <Button
              size="sm"
              asChild
              className={cn(
                "h-9 px-5 font-medium transition-all",
                scrolled
                  ? "bg-primary hover:bg-primary/90 text-white shadow-sm"
                  : "bg-white/15 text-white border border-white/25 hover:bg-white/25 backdrop-blur-sm",
              )}
            >
              <Link to="/login" className="inline-flex items-center gap-1.5">
                Get Started <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-md transition-colors hover:bg-white/10"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? (
            <X
              className={cn(
                "h-5 w-5",
                scrolled ? "text-foreground" : "text-white",
              )}
            />
          ) : (
            <Menu
              className={cn(
                "h-5 w-5",
                scrolled ? "text-foreground" : "text-white",
              )}
            />
          )}
        </button>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <div className="md:hidden bg-background/98 backdrop-blur-lg border-b shadow-lg">
          <div className="container mx-auto px-4 py-4 space-y-1">
            {NAV_LINKS.map((link, idx) => {
              const isActive = activeSection === link.target;
              const prevGroup = idx > 0 ? NAV_LINKS[idx - 1]?.group : link.group;
              const showDivider = idx > 0 && prevGroup !== link.group;
              return (
                <div key={link.target}>
                  {showDivider && <hr className="my-2 border-border/40" />}
                  <button
                    onClick={() => handleNav(link.target)}
                    className={cn(
                      "block w-full text-left px-3 py-2.5 text-sm font-medium rounded-md transition-colors",
                      isActive
                        ? "text-primary bg-primary/5"
                        : "text-foreground hover:bg-muted/50",
                    )}
                  >
                    {link.label}
                  </button>
                </div>
              );
            })}
            <hr className="my-3 border-border/50" />
            {isAuthenticated && user ? (
              <Button
                size="sm"
                asChild
                className="w-full bg-primary hover:bg-primary/90 text-white"
              >
                <Link
                  to={DASHBOARD_ROUTES[user.role].path}
                  className="inline-flex items-center justify-center gap-1.5"
                >
                  <LayoutDashboard className="h-3.5 w-3.5" />
                  {DASHBOARD_ROUTES[user.role].label}
                </Link>
              </Button>
            ) : (
              <Button
                size="sm"
                asChild
                className="w-full bg-primary hover:bg-primary/90 text-white"
              >
                <Link
                  to="/login"
                  className="inline-flex items-center justify-center gap-1.5"
                >
                  Get Started <ChevronRight className="h-3.5 w-3.5" />
                </Link>
              </Button>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}

export default Navbar;
