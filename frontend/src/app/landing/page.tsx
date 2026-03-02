/**
 * Landing Page
 *
 * Public-facing page at "/" that showcases the Floodingnaque system
 * for the thesis defense. Composes all landing sections in order.
 */

import { Navbar } from './components/Navbar';
import { HeroSection } from './components/HeroSection';
import { LiveStatusRibbon } from './components/LiveStatusRibbon';
import { StatsRow } from './components/StatsRow';
import { HowItWorks } from './components/HowItWorks';
import { FeatureCards } from './components/FeatureCards';
import { RiskExplainer } from './components/RiskExplainer';
import { BarangayMapSection } from './components/BarangayMapSection';
import { DualCTA } from './components/DualCTA';
import { Footer } from './components/Footer';

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
      <BarangayMapSection />
      <DualCTA />
      <Footer />
    </div>
  );
}
