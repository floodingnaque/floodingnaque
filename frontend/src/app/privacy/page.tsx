/**
 * Privacy Policy Page
 *
 * Comprehensive Privacy Policy aligned with the Philippine Data Privacy Act
 * of 2012 (RA 10173) and its Implementing Rules and Regulations.
 * Covers the Floodingnaque Flood Prediction & Early Warning System for
 * Parañaque City, Metro Manila, Philippines.
 */

import { RainEffect } from "@/components/effects/RainEffect";
import { FloodIcon } from "@/components/icons/FloodIcon";
import { Separator } from "@/components/ui/separator";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

export function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Hero header bar */}
      <div className="relative bg-linear-to-br from-primary via-primary/95 to-primary/80 overflow-hidden ring-1 ring-white/10 shadow-2xl">
        <RainEffect density={20} opacity={0.08} />
        <div className="absolute inset-0 bg-linear-to-b from-black/20 via-transparent to-black/30" />
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-linear-to-r from-primary/60 via-primary to-primary/60" />
        <div className="relative z-10 container mx-auto px-6 py-12 md:py-16">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-sm text-white/60 hover:text-white transition-colors mb-6 rounded-full bg-white/5 backdrop-blur-sm px-3 py-1.5 border border-white/10 hover:border-white/20"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Login
          </Link>
          <div className="flex items-center gap-3 mb-3">
            <div className="h-10 w-10 rounded-xl bg-white/10 ring-1 ring-white/20 flex items-center justify-center">
              <FloodIcon className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-bold text-white tracking-tight">
              Floodingnaque
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            Privacy Policy
          </h1>
          <p className="text-sm text-white/50 mt-2">
            Effective date: March 1, 2026 &middot; Last updated: March 3, 2026
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-10 md:py-14">
        <div className="mx-auto max-w-3xl rounded-2xl border border-border/30 bg-card/50 backdrop-blur-sm p-8 md:p-10 shadow-lg ring-1 ring-white/5 space-y-8 text-sm leading-relaxed text-muted-foreground [&_h2]:text-foreground [&_strong]:text-foreground">
          {/* ---- 1 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">1. Introduction</h2>
            <p>
              This Privacy Policy describes how the Floodingnaque Flood
              Prediction &amp; Early Warning System (&ldquo;Service,&rdquo;
              &ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;)
              collects, processes, stores, and protects Personal Information
              from users (&ldquo;you&rdquo; or &ldquo;Data Subject&rdquo;) in
              accordance with Republic Act No.&nbsp;10173, the{" "}
              <strong>Data Privacy Act of 2012</strong> (&ldquo;DPA&rdquo;), its
              Implementing Rules and Regulations (&ldquo;IRR&rdquo;), and
              issuances of the National Privacy Commission (&ldquo;NPC&rdquo;).
            </p>
            <p>
              By creating an account or using the Service, you acknowledge that
              you have read, understood, and agree to the collection and
              processing of your Personal Information as described herein. If
              you do not agree, you must not use the Service.
            </p>
          </section>

          <Separator />

          {/* ---- 2 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              2. Data Controller &amp; Contact Information
            </h2>
            <p>
              The Floodingnaque project is an academic thesis developed in
              collaboration with the Parañaque City Disaster Risk Reduction and
              Management Office (&ldquo;DRRMO&rdquo;). For the purposes of the
              DPA, the project team acts as the Personal Information Controller.
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>
                <strong>Email:</strong> floodingnaque@gmail.com
              </li>
              <li>
                <strong>Location:</strong> Parañaque City, Metro Manila,
                Philippines
              </li>
            </ul>
            <p>
              For privacy-related concerns, complaints, or requests to exercise
              your data subject rights, please contact us at the email address
              above or file a complaint directly with the{" "}
              <strong>National Privacy Commission</strong> at{" "}
              <em>complaints@privacy.gov.ph</em>.
            </p>
          </section>

          <Separator />

          {/* ---- 3 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              3. Personal Information We Collect
            </h2>
            <p>
              We collect the minimum information necessary to operate the
              Service and fulfill its disaster-preparedness mission:
            </p>
            <ul className="list-disc pl-6 space-y-1.5">
              <li>
                <strong>Account Information:</strong> Full name, email address,
                and optional phone number provided during registration.
              </li>
              <li>
                <strong>Authentication Data:</strong> Passwords (stored only as
                bcrypt hashes &mdash; we never store plaintext passwords), login
                timestamps, and session identifiers.
              </li>
              <li>
                <strong>Network &amp; Device Data:</strong> IP address at the
                time of login, browser type, and operating system. IP addresses
                are retained for security purposes and automatically purged
                after ninety (90) days.
              </li>
              <li>
                <strong>Usage Data:</strong> Flood prediction requests, alert
                acknowledgments, dashboard interactions, and feature usage
                patterns &mdash; collected in aggregate and anonymized form.
              </li>
              <li>
                <strong>Location Preferences:</strong> Barangay or area
                selections within Parañaque City that you configure to receive
                localized flood alerts. We do not collect precise GPS
                coordinates from your device.
              </li>
            </ul>
          </section>

          <Separator />

          {/* ---- 4 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              4. Purposes &amp; Legal Basis for Processing
            </h2>
            <p>
              Under the DPA and its IRR, we process your Personal Information
              based on one or more of the following lawful criteria:
            </p>
            <ul className="list-disc pl-6 space-y-1.5">
              <li>
                <strong>Consent (Section 12(a), DPA):</strong> You provide
                consent when you create an account and agree to this Privacy
                Policy.
              </li>
              <li>
                <strong>Performance of a Contract (Section 12(b), DPA):</strong>{" "}
                Processing is necessary to deliver flood predictions, risk
                alerts, and other Service features you have requested.
              </li>
              <li>
                <strong>Legitimate Interest (Section 12(f), DPA):</strong>{" "}
                Securing the Service against unauthorized access, detecting
                abuse, enforcing rate limits, and improving the machine-learning
                model through aggregated, de-identified analytics.
              </li>
              <li>
                <strong>
                  Public Safety &amp; Disaster Preparedness (Section 4(e), DPA):
                </strong>{" "}
                The Service processes environmental data (rainfall, temperature,
                humidity) obtained from government agencies including PAGASA and
                the NDRRMC to generate flood risk assessments that protect life
                and property.
              </li>
            </ul>
          </section>

          <Separator />

          {/* ---- 5 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              5. How We Use Your Information
            </h2>
            <ul className="list-disc pl-6 space-y-1.5">
              <li>
                Authenticate your identity and authorize access to protected
                features.
              </li>
              <li>
                Generate and deliver flood predictions and three-level risk
                classifications (Safe, Alert, Critical) for Parañaque City
                barangays.
              </li>
              <li>
                Send time-sensitive flood alerts and weather advisories via the
                dashboard and, where applicable, email or SMS notifications.
              </li>
              <li>
                Detect, prevent, and respond to security incidents including
                brute-force attacks, credential stuffing, and unauthorized API
                access.
              </li>
              <li>
                Improve model accuracy and Service reliability through
                aggregated, anonymized usage statistics. Individual prediction
                requests are never shared in identifiable form.
              </li>
              <li>
                Fulfill academic research requirements for the thesis project
                &mdash; all published data is anonymized and aggregated.
              </li>
            </ul>
          </section>

          <Separator />

          {/* ---- 6 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">6. Data Retention</h2>
            <p>
              We retain your Personal Information only for as long as necessary
              to fulfill the purposes described in this Policy:
            </p>
            <ul className="list-disc pl-6 space-y-1.5">
              <li>
                <strong>Account data</strong> is retained while your account
                remains active. You may request deletion at any time.
              </li>
              <li>
                <strong>Login IP addresses</strong> are automatically purged
                after ninety (90) days.
              </li>
              <li>
                <strong>Authentication tokens</strong> (JWT access tokens)
                expire after fifteen (15) minutes. Refresh tokens are stored as
                SHA-256 hashes and are revoked upon logout or after inactivity.
              </li>
              <li>
                <strong>Deleted accounts:</strong> Upon account deletion, all
                personally identifiable information is scrubbed. Only an
                anonymized, non-reversible record may be retained to preserve
                data integrity and prevent re-registration abuse.
              </li>
              <li>
                <strong>Flood &amp; weather data</strong> collected from public
                agencies (DRRMO, PAGASA) does not contain Personal Information
                and is retained indefinitely for research and model training.
              </li>
            </ul>
          </section>

          <Separator />

          {/* ---- 7 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              7. Your Rights as a Data Subject
            </h2>
            <p>
              Under the DPA (Sections 16&ndash;18) and NPC issuances, you have
              the following rights:
            </p>
            <ul className="list-disc pl-6 space-y-1.5">
              <li>
                <strong>Right to Be Informed:</strong> You have the right to
                know the extent and manner in which your Personal Information is
                being processed, which is the purpose of this Policy.
              </li>
              <li>
                <strong>Right to Access:</strong> You may request a copy of all
                Personal Information we hold about you. Use the &ldquo;Export My
                Data&rdquo; feature in your Account Settings or email us
                directly.
              </li>
              <li>
                <strong>Right to Rectification:</strong> You may update or
                correct inaccurate Personal Information through your Account
                Settings at any time.
              </li>
              <li>
                <strong>Right to Erasure / Blocking:</strong> You may request
                the deletion of your account and all associated Personal
                Information via Account Settings or by contacting us.
              </li>
              <li>
                <strong>Right to Object:</strong> You may object to the
                processing of your Personal Information at any time on
                legitimate grounds. Contact us at{" "}
                <em>floodingnaque@gmail.com</em>.
              </li>
              <li>
                <strong>Right to Data Portability:</strong> You may request your
                Personal Information in a structured, commonly used, and
                machine-readable format.
              </li>
              <li>
                <strong>Right to File a Complaint:</strong> You may lodge a
                complaint with the National Privacy Commission if you believe
                your data privacy rights have been violated.
              </li>
            </ul>
            <p>
              We will respond to verified requests within fifteen (15) business
              days, as required by the DPA and its IRR.
            </p>
          </section>

          <Separator />

          {/* ---- 8 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">8. Data Security</h2>
            <p>
              We implement reasonable and appropriate organizational, physical,
              and technical security measures to protect your Personal
              Information against unauthorized access, alteration, disclosure,
              or destruction:
            </p>
            <ul className="list-disc pl-6 space-y-1.5">
              <li>
                <strong>Encryption at rest &amp; in transit:</strong> All
                network traffic is encrypted via TLS. Sensitive configuration
                values and credentials are managed through Docker Secrets or
                environment variables &mdash; never stored in source code.
              </li>
              <li>
                <strong>Password security:</strong> Passwords are hashed using
                bcrypt with an appropriate work factor. We never store or log
                plaintext passwords.
              </li>
              <li>
                <strong>Token management:</strong> JWT access tokens expire
                after fifteen (15) minutes. Refresh tokens are stored as SHA-256
                hashes and are rotated upon each use.
              </li>
              <li>
                <strong>Access controls:</strong> Role-based access control
                (RBAC) ensures that administrative functions are restricted to
                authorized personnel. All administrative actions are logged.
              </li>
              <li>
                <strong>Rate limiting &amp; abuse prevention:</strong> IP-based
                rate limiting, account lockout policies, and request size
                validation protect against brute-force attacks and denial of
                service.
              </li>
              <li>
                <strong>Model integrity:</strong> Machine-learning model files
                are verified using HMAC signatures before loading to prevent
                tampering.
              </li>
            </ul>
            <p>
              While we strive to protect your data, no method of electronic
              transmission or storage is completely secure. We cannot guarantee
              absolute security.
            </p>
          </section>

          <Separator />

          {/* ---- 9 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              9. Cookies &amp; Local Storage
            </h2>
            <p>
              The Service uses browser local storage to persist authentication
              tokens and user interface preferences (e.g., dark mode setting,
              sidebar state). We do not use third-party tracking cookies or
              advertising cookies.
            </p>
            <p>
              Essential storage items cannot be disabled without impairing core
              Service functionality. No analytics or marketing trackers are
              embedded in the Service.
            </p>
          </section>

          <Separator />

          {/* ---- 10 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">10. Third-Party Services</h2>
            <p>
              To deliver accurate flood predictions, the Service integrates with
              external data sources. These integrations are limited to fetching
              publicly available environmental data and do not involve sharing
              your Personal Information:
            </p>
            <ul className="list-disc pl-6 space-y-1.5">
              <li>
                <strong>Meteostat:</strong> Historical and real-time weather
                observations.
              </li>
              <li>
                <strong>OpenWeatherMap:</strong> Current weather conditions and
                forecasts.
              </li>
              <li>
                <strong>Google Earth Engine:</strong> Satellite-derived
                environmental data.
              </li>
              <li>
                <strong>PAGASA &amp; NDRRMC:</strong> Official Philippine
                weather bulletins and disaster advisories.
              </li>
            </ul>
            <p>
              Each third-party service operates under its own privacy policy. We
              encourage you to review their policies independently. We do not
              sell, trade, or rent your Personal Information to any third party.
            </p>
          </section>

          <Separator />

          {/* ---- 11 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              11. Data Sharing &amp; Disclosure
            </h2>
            <p>
              We do not sell your Personal Information. We may disclose your
              data only in the following limited circumstances:
            </p>
            <ul className="list-disc pl-6 space-y-1.5">
              <li>
                <strong>Law enforcement or legal process:</strong> When required
                by a valid court order, subpoena, or other legal obligation
                under Philippine law.
              </li>
              <li>
                <strong>Protection of rights:</strong> To enforce our Terms of
                Service or protect the safety of our users and the public.
              </li>
              <li>
                <strong>Academic research:</strong> Aggregated, anonymized, and
                de-identified data may be included in thesis publications,
                academic papers, or presentations. No individually identifiable
                data is ever published.
              </li>
              <li>
                <strong>Service providers:</strong> Trusted hosting and
                infrastructure providers who process data on our behalf under
                strict confidentiality agreements.
              </li>
            </ul>
          </section>

          <Separator />

          {/* ---- 12 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              12. Cross-Border Data Transfers
            </h2>
            <p>
              The Service may utilize cloud infrastructure and third-party APIs
              with servers located outside the Philippines. In such cases, we
              ensure that appropriate safeguards are in place, including
              contractual obligations that provide a level of data protection
              consistent with the DPA and NPC Circular No.&nbsp;2016-02.
            </p>
          </section>

          <Separator />

          {/* ---- 13 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              13. Data Breach Notification
            </h2>
            <p>
              In the event of a personal data breach that is likely to cause
              serious harm to affected Data Subjects, we will:
            </p>
            <ul className="list-disc pl-6 space-y-1.5">
              <li>
                Notify the <strong>National Privacy Commission</strong> within
                seventy-two (72) hours of becoming aware of the breach, in
                accordance with NPC Circular No.&nbsp;2016-03.
              </li>
              <li>
                Notify affected Data Subjects without undue delay, providing
                information about the nature of the breach, the data involved,
                and recommended protective measures.
              </li>
              <li>
                Document the breach, its effects, and remedial actions taken in
                our internal incident register.
              </li>
            </ul>
          </section>

          <Separator />

          {/* ---- 14 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              14. Children&rsquo;s Privacy
            </h2>
            <p>
              The Service is not directed at children under the age of fifteen
              (15). We do not knowingly collect Personal Information from
              children under 15. If we become aware that we have inadvertently
              collected such data, we will take immediate steps to delete it.
              Parents or guardians who believe their child has provided Personal
              Information to us should contact us at{" "}
              <em>floodingnaque@gmail.com</em>.
            </p>
          </section>

          <Separator />

          {/* ---- 15 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">
              15. Changes to This Privacy Policy
            </h2>
            <p>
              We reserve the right to update this Privacy Policy at any time to
              reflect changes in our practices, legal requirements, or Service
              features. Material changes will be communicated to registered
              users via in-app notification or email at least fifteen (15) days
              before taking effect.
            </p>
            <p>
              The &ldquo;Last updated&rdquo; date at the top of this page
              indicates when this Policy was last revised. Continued use of the
              Service after the effective date of any changes constitutes your
              acceptance of the updated Policy.
            </p>
          </section>

          <Separator />

          {/* ---- 16 ---- */}
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">16. Governing Law</h2>
            <p>
              This Privacy Policy shall be governed by and construed in
              accordance with the laws of the Republic of the Philippines,
              including but not limited to:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>
                Republic Act No.&nbsp;10173 &mdash; Data Privacy Act of 2012
              </li>
              <li>
                NPC Circular No.&nbsp;2016-01 &mdash; Rules of Procedure of the
                NPC
              </li>
              <li>
                NPC Circular No.&nbsp;2016-02 &mdash; Data Sharing Agreements
              </li>
              <li>
                NPC Circular No.&nbsp;2016-03 &mdash; Personal Data Breach
                Management
              </li>
            </ul>
            <p>
              Any disputes arising from this Policy shall be subject to the
              exclusive jurisdiction of the courts of Parañaque City, Metro
              Manila, Philippines.
            </p>
          </section>

          <Separator />

          {/* ---- 17 ---- */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold">17. Contact Us</h2>
            <p>
              If you have any questions, concerns, or requests regarding this
              Privacy Policy or the processing of your Personal Information,
              please contact us:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>
                <strong>Email:</strong> floodingnaque@gmail.com
              </li>
              <li>
                <strong>Location:</strong> Parañaque City, Metro Manila,
                Philippines
              </li>
            </ul>
            <p>
              You may also file a complaint with the National Privacy
              Commission:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>
                <strong>NPC Website:</strong> https://privacy.gov.ph
              </li>
              <li>
                <strong>NPC Email:</strong> complaints@privacy.gov.ph
              </li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}

export default PrivacyPage;
