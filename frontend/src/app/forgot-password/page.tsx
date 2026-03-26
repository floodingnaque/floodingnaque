/**
 * Forgot Password Page - Professional & Industrial Grade
 *
 * Public page for resetting a forgotten password.
 * Uses shared AuthPageLayout with branding panel.
 * Supports direct reset links via ?token=...&email=... query params.
 */

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { AuthPageLayout } from "@/features/auth/components/AuthPageLayout";
import { ForgotPasswordForm } from "@/features/auth/components/ForgotPasswordForm";
import { useAuthStore } from "@/state/stores/authStore";

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  if (isAuthenticated) {
    return null;
  }

  return (
    <AuthPageLayout
      backTo="/login"
      backLabel="Back to sign in"
      showBrandingPanel
    >
      <ForgotPasswordForm />
    </AuthPageLayout>
  );
}

export default ForgotPasswordPage;
