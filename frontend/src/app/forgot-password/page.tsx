/**
 * Forgot Password Page
 *
 * Public page for resetting a forgotten password.
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Droplets } from 'lucide-react';

import { useAuthStore } from '@/state/stores/authStore';
import { ForgotPasswordForm } from '@/features/auth/components/ForgotPasswordForm';

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Logo */}
        <div className="flex flex-col items-center space-y-2 text-center">
          <div className="flex items-center justify-center h-16 w-16 rounded-full bg-primary/10">
            <Droplets className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Floodingnaque</h1>
          <p className="text-muted-foreground">
            Flood Prediction & Monitoring System
          </p>
        </div>

        <ForgotPasswordForm />
      </div>
    </div>
  );
}

export default ForgotPasswordPage;
