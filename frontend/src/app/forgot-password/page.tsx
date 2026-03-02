/**
 * Forgot Password Page
 *
 * Public page for resetting a forgotten password.
 * Themed to match the login page (dark primary hero style).
 */

import { useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Droplets, ArrowLeft } from 'lucide-react';

import { useAuthStore } from '@/state/stores/authStore';
import { ForgotPasswordForm } from '@/features/auth/components/ForgotPasswordForm';
import { RainEffect } from '@/components/effects/RainEffect';

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-primary overflow-hidden p-4">
      {/* Rain effect — matches LoginPage */}
      <RainEffect />

      {/* Gradient overlay — matches HeroSection / LoginPage */}
      <div className="absolute inset-0 bg-linear-to-b from-black/20 via-transparent to-black/30" />

      {/* Back to login */}
      <Link
        to="/login"
        className="absolute top-6 left-6 z-20 inline-flex items-center gap-1.5 text-sm text-white/60 hover:text-white transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to login
      </Link>

      <div className="relative z-10 w-full max-w-md space-y-6">
        {/* Logo */}
        <div className="flex flex-col items-center space-y-2 text-center">
          <div className="flex items-center justify-center h-16 w-16 rounded-full bg-white/15 backdrop-blur-sm">
            <Droplets className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Floodingnaque</h1>
          <p className="text-white/60">
            Flood Prediction & Monitoring System
          </p>
        </div>

        <ForgotPasswordForm />
      </div>
    </div>
  );
}

export default ForgotPasswordPage;
