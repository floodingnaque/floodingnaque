/**
 * Landing Page
 *
 * Public-facing page at "/" that showcases the Floodingnaque system
 * for the thesis defense. Composes all landing sections in order.
 */

import { BarangayStatusSection } from "./components/BarangayStatusSection";
import { CityWideBroadcastSection } from "./components/CityWideBroadcastSection";
import { DualCTA } from "./components/DualCTA";
import { FeatureCards } from "./components/FeatureCards";
import { Footer } from "./components/Footer";
import { HeroSection } from "./components/HeroSection";
import { HowItWorks } from "./components/HowItWorks";
import { LiveStatusRibbon } from "./components/LiveStatusRibbon";
import { Navbar } from "./components/Navbar";
import { RiskExplainer } from "./components/RiskExplainer";
import { StatsRow } from "./components/StatsRow";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background scroll-smooth antialiased">
      <Navbar />
      <HeroSection />
      <LiveStatusRibbon />
      <StatsRow />
      <HowItWorks />
      <FeatureCards />
      <RiskExplainer />
      <BarangayStatusSection />
      <CityWideBroadcastSection />
      <DualCTA />
      <Footer />
    </div>
  );
}
