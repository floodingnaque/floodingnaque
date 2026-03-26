/**
 * Login Page - Professional & Industrial Grade
 *
 * Split-panel layout: left branding panel (desktop) + right login form.
 * Redirects authenticated users. Consistent emergency management theme.
 */

import { motion } from "framer-motion";
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getDefaultRoute } from "@/config/role-routes";
import { AuthPageLayout } from "@/features/auth/components/AuthPageLayout";
import { LoginForm } from "@/features/auth/components/LoginForm";
import { useAuthStore } from "@/state/stores/authStore";

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: "easeOut" as const },
  },
} as const;

export function LoginPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const userRole = useAuthStore((state) => state.user?.role);

  useEffect(() => {
    if (isAuthenticated) {
      navigate(getDefaultRoute(userRole), { replace: true });
    }
  }, [isAuthenticated, userRole, navigate]);

  if (isAuthenticated) return null;

  return (
    <AuthPageLayout showBrandingPanel backTo="/" backLabel="Back to home">
      <motion.div
        initial="hidden"
        animate="show"
        variants={{
          hidden: { opacity: 0 },
          show: { opacity: 1, transition: { staggerChildren: 0.12 } },
        }}
        className="space-y-4"
      >
        <LoginForm />

        {/* Footer legal links */}
        <motion.p
          variants={itemVariants}
          className="text-center text-xs text-white/35"
        >
          By continuing, you agree to our{" "}
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
        </motion.p>
      </motion.div>
    </AuthPageLayout>
  );
}

export default LoginPage;
