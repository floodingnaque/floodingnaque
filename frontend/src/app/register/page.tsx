/**
 * Registration Page — Multi-step Resident Onboarding
 *
 * Uses a split-panel layout (branding left, form right on desktop).
 * Redirects authenticated users.
 */

import { motion } from "framer-motion";
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AuthPageLayout } from "@/features/auth/components/AuthPageLayout";
import { RegistrationWizard } from "@/features/auth/components/RegistrationWizard";
import { useAuthStore } from "@/state/stores/authStore";

export function RegisterPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  if (isAuthenticated) return null;

  return (
    <AuthPageLayout
      showBrandingPanel
      backTo="/login"
      backLabel="Back to sign in"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
        className="space-y-4"
      >
        <RegistrationWizard />

        <p className="text-center text-xs text-white/35">
          By registering, you agree to our{" "}
          <Link
            to="/terms"
            className="underline hover:text-white/60 transition-colors"
          >
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link
            to="/privacy"
            className="underline hover:text-white/60 transition-colors"
          >
            Privacy Policy
          </Link>
          .
        </p>
      </motion.div>
    </AuthPageLayout>
  );
}

export default RegisterPage;
