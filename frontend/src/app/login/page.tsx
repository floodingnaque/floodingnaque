/**
 * Login Page
 *
 * Authentication page with tabbed login and registration forms.
 * Themed to match the landing page (dark primary hero style).
 * Redirects authenticated users to dashboard.
 */

import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Droplets, ArrowLeft } from 'lucide-react';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuthStore } from '@/state/stores/authStore';

import { LoginForm } from '@/features/auth/components/LoginForm';
import { RegisterForm } from '@/features/auth/components/RegisterForm';

/**
 * LoginPage component with tabbed authentication forms
 */
export function LoginPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const [activeTab, setActiveTab] = useState<string>('login');

  // Redirect if already authenticated (e.g. user hits /login via back button).
  // We do NOT use `from` here — role-based destination is handled by useAuth.ts.
  // Using `from` here caused LoginPage to override navigate('/admin') with navigate('/').
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Don't render the form if redirecting
  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-primary overflow-hidden p-4">
      {/* Gradient overlay — matches HeroSection */}
      <div className="absolute inset-0 bg-linear-to-b from-black/20 via-transparent to-black/30" />

      {/* Back to landing */}
      <Link
        to="/"
        className="absolute top-6 left-6 z-20 inline-flex items-center gap-1.5 text-sm text-white/60 hover:text-white transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to home
      </Link>

      <div className="relative z-10 w-full max-w-md space-y-6">
        {/* Logo and Title */}
        <div className="flex flex-col items-center space-y-2 text-center">
          <div className="flex items-center justify-center h-16 w-16 rounded-full bg-white/15 backdrop-blur-sm">
            <Droplets className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Floodingnaque</h1>
          <p className="text-white/60">
            Flood Prediction & Monitoring System
          </p>
        </div>

        {/* Auth Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 bg-white/10 border border-white/10">
            <TabsTrigger
              value="login"
              className="text-white/70 data-[state=active]:bg-white data-[state=active]:text-primary data-[state=active]:font-semibold"
            >
              Login
            </TabsTrigger>
            <TabsTrigger
              value="register"
              className="text-white/70 data-[state=active]:bg-white data-[state=active]:text-primary data-[state=active]:font-semibold"
            >
              Register
            </TabsTrigger>
          </TabsList>
          <TabsContent value="login" className="mt-4">
            <LoginForm onSwitchToRegister={() => setActiveTab('register')} />
          </TabsContent>
          <TabsContent value="register" className="mt-4">
            <RegisterForm onSwitchToLogin={() => setActiveTab('login')} />
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <p className="text-center text-xs text-white/40">
          By continuing, you agree to our{' '}
          <Link to="/terms" className="underline hover:text-white/70">Terms of Service</Link>{' '}
          and{' '}
          <Link to="/privacy" className="underline hover:text-white/70">Privacy Policy</Link>.
        </p>
      </div>
    </div>
  );
}

export default LoginPage;