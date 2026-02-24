/**
 * Login Page
 *
 * Authentication page with tabbed login and registration forms.
 * Redirects authenticated users to dashboard.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Droplets } from 'lucide-react';

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
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Don't render the form if redirecting
  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-background to-muted p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Logo and Title */}
        <div className="flex flex-col items-center space-y-2 text-center">
          <div className="flex items-center justify-center h-16 w-16 rounded-full bg-primary/10">
            <Droplets className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Floodingnaque</h1>
          <p className="text-muted-foreground">
            Flood Prediction & Monitoring System
          </p>
        </div>

        {/* Auth Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="login">Login</TabsTrigger>
            <TabsTrigger value="register">Register</TabsTrigger>
          </TabsList>
          <TabsContent value="login" className="mt-4">
            <LoginForm onSwitchToRegister={() => setActiveTab('register')} />
          </TabsContent>
          <TabsContent value="register" className="mt-4">
            <RegisterForm onSwitchToLogin={() => setActiveTab('login')} />
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground">
          By continuing, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}

export default LoginPage;