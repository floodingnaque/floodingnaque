/**
 * Terms of Service Page
 *
 * Themed with a primary header banner to match the system design language.
 */

import { Link } from 'react-router-dom';
import { ArrowLeft, Droplets } from 'lucide-react';

export function TermsPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Hero header bar */}
      <div className="relative bg-primary overflow-hidden">
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
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">Terms of Service</h1>
          <p className="text-sm text-white/50 mt-2">Last updated: March 1, 2026</p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-10 md:py-14">
      <div className="mx-auto max-w-3xl space-y-8">

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">1. Acceptance of Terms</h2>
          <p>
            By accessing or using the Floodingnaque Flood Prediction &amp; Monitoring
            System (&quot;Service&quot;), you agree to be bound by these Terms of Service.
            If you do not agree, do not use the Service.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">2. Description of Service</h2>
          <p>
            Floodingnaque provides flood risk predictions, weather monitoring, and
            alerting capabilities for Naga City, Camarines Sur. The Service is
            developed as part of an academic thesis and is provided on an
            &quot;as-is&quot; basis for research and informational purposes.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">3. User Accounts</h2>
          <p>
            You are responsible for maintaining the confidentiality of your account
            credentials. You agree to provide accurate information when registering
            and to keep your account information up to date.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">4. Acceptable Use</h2>
          <p>You agree not to:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Use the Service for any unlawful purpose.</li>
            <li>Attempt to gain unauthorized access to the system.</li>
            <li>Interfere with or disrupt the Service.</li>
            <li>Scrape, crawl, or use automated tools to extract data beyond the provided API.</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">5. Disclaimer of Warranties</h2>
          <p>
            Flood predictions are based on machine-learning models and publicly
            available meteorological data. They are approximations and must
            <strong> not</strong> be used as the sole basis for emergency
            decision-making. Always follow official government advisories.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">6. Limitation of Liability</h2>
          <p>
            To the maximum extent permitted by law, the developers of
            Floodingnaque shall not be liable for any indirect, incidental, or
            consequential damages arising from the use of the Service.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">7. Data &amp; Privacy</h2>
          <p>
            Your use of the Service is also governed by our{' '}
            <Link to="/privacy" className="text-primary underline">
              Privacy Policy
            </Link>
            .
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">8. Changes to Terms</h2>
          <p>
            We reserve the right to modify these Terms at any time. Continued use
            of the Service after changes constitutes acceptance of the updated Terms.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">9. Contact</h2>
          <p>
            For questions about these Terms, contact the project maintainers via
            the repository listed in the project README.
          </p>
        </section>
      </div>
      </div>
    </div>
  );
}

export default TermsPage;
