/**
 * Privacy Policy Page
 *
 * Covers GDPR / Philippine Data Privacy Act (RA 10173) requirements.
 * Themed with a primary header banner to match the system design language.
 */

import { Link } from 'react-router-dom';
import { ArrowLeft, Droplets } from 'lucide-react';
import { RainEffect } from '@/components/effects/RainEffect';

export function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Hero header bar */}
      <div className="relative bg-primary overflow-hidden">
        <RainEffect density={20} opacity={0.08} />
        <div className="absolute inset-0 bg-linear-to-b from-black/20 via-transparent to-black/30" />
        <div className="relative z-10 container mx-auto px-6 py-12 md:py-16">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-sm text-white/60 hover:text-white transition-colors mb-6"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Login
          </Link>
          <div className="flex items-center gap-3 mb-3">
            <div className="h-10 w-10 rounded-lg bg-white/15 flex items-center justify-center">
              <Droplets className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-bold text-white tracking-tight">Floodingnaque</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">Privacy Policy</h1>
          <p className="text-sm text-white/50 mt-2">Last updated: March 1, 2026</p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-10 md:py-14">
      <div className="mx-auto max-w-3xl space-y-8">

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">1. Introduction</h2>
          <p>
            This Privacy Policy explains how the Floodingnaque Flood Prediction &amp;
            Monitoring System (&quot;Service&quot;) collects, uses, and protects your
            personal data in compliance with the Philippine Data Privacy Act of 2012
            (RA 10173) and the EU General Data Protection Regulation (GDPR).
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">2. Data We Collect</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Account data:</strong> email address, full name, phone number (optional).</li>
            <li><strong>Authentication data:</strong> hashed password, login timestamps.</li>
            <li><strong>Network data:</strong> IP address at login (retained for up to 90 days, then automatically purged).</li>
            <li><strong>Usage data:</strong> prediction requests, alert acknowledgments.</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">3. How We Use Your Data</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>Authenticate and authorize access to the Service.</li>
            <li>Deliver flood predictions and alerts.</li>
            <li>Detect and prevent unauthorized access (IP-based rate limiting and lockout).</li>
            <li>Improve model accuracy through aggregated, anonymized usage statistics.</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">4. Legal Basis for Processing</h2>
          <p>
            We process your data based on: (a) your consent when you create an account,
            (b) legitimate interest in securing the Service, and (c) compliance with
            applicable laws.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">5. Data Retention</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>Account data is retained while your account is active.</li>
            <li>Login IP addresses are automatically purged after 90 days.</li>
            <li>Deleted accounts have personal data scrubbed; only an anonymized record is kept to maintain data integrity.</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">6. Your Rights</h2>
          <p>You have the right to:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Access</strong> your personal data (<code>GET /api/v1/users/me/export</code>).</li>
            <li><strong>Delete</strong> your account and have your personal data erased (<code>DELETE /api/v1/users/me</code>).</li>
            <li><strong>Rectify</strong> inaccurate personal data via your account settings.</li>
            <li><strong>Object</strong> to processing by contacting us.</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">7. Data Security</h2>
          <p>
            Passwords are hashed using bcrypt. Network traffic is encrypted via TLS.
            Access tokens expire after 15 minutes. Refresh tokens are stored as
            SHA-256 hashes.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">8. Third-Party Services</h2>
          <p>
            The Service may use third-party APIs (weather data, geospatial services).
            These providers have their own privacy policies. We do not share your
            personal data with them.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">9. Changes to This Policy</h2>
          <p>
            We may update this Privacy Policy from time to time. We will notify
            registered users of material changes via the Service.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">10. Contact</h2>
          <p>
            For privacy-related inquiries, contact the project maintainers via
            the repository listed in the project README, or reach out to the
            thesis adviser at the relevant academic institution.
          </p>
        </section>
      </div>
      </div>
    </div>
  );
}

export default PrivacyPage;
