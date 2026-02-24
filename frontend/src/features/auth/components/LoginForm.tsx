/**
 * LoginForm Component
 *
 * Login form with email and password validation.
 * Uses react-hook-form with zod validation.
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useEffect, useRef } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

import { useAuth } from '../hooks/useAuth';
import { useAuthStore } from '@/state/stores/authStore';

/**
 * Login form validation schema
 */
const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters'),
});

type LoginFormData = z.infer<typeof loginSchema>;

/**
 * LoginForm component props
 */
interface LoginFormProps {
  /** Callback when switching to register tab */
  onSwitchToRegister?: () => void;
}

/**
 * LoginForm renders a login form with validation
 */
export function LoginForm({ onSwitchToRegister }: LoginFormProps) {
  const { login, isLoggingIn, loginError } = useAuth();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  // Navigate after login based on role. This runs inside the component tree
  // where useNavigate is always connected to the router — unlike calling
  // navigate() inside a mutation onSuccess which can be stale/disconnected.
  useEffect(() => {
    if (isAuthenticated && user) {
      navigate(user.role === 'admin' ? '/admin' : '/', { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  // Auto-focus first field on mount
  const emailRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    emailRef.current?.focus();
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  // Combine react-hook-form ref with our focus ref
  const { ref: emailRegRef, ...emailRegRest } = register('email');

  const onSubmit = (data: LoginFormData) => {
    login(data);
  };

  // Extract error message from loginError
  const errorMessage = loginError
    ? (loginError as { message?: string }).message || 'Login failed. Please try again.'
    : null;

  return (
    <Card className="w-full">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold">Welcome back</CardTitle>
        <CardDescription>
          Enter your credentials to access your account
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* API Error Alert */}
          {errorMessage && (
            <Alert variant="destructive" role="alert" aria-live="assertive">
              <AlertCircle className="h-4 w-4" aria-hidden="true" />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}

          {/* Email Field */}
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="name@example.com"
              autoComplete="email"
              disabled={isLoggingIn}
              {...emailRegRest}
              ref={(e) => {
                emailRegRef(e);
                emailRef.current = e;
              }}
              aria-invalid={!!errors.email}
              aria-describedby={errors.email ? 'email-error' : undefined}
            />
            {errors.email && (
              <p id="email-error" className="text-sm text-destructive" role="alert">
                {errors.email.message}
              </p>
            )}
          </div>

          {/* Password Field */}
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Enter your password"
              autoComplete="current-password"
              disabled={isLoggingIn}
              {...register('password')}
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? 'password-error' : undefined}
            />
            {errors.password && (
              <p id="password-error" className="text-sm text-destructive" role="alert">
                {errors.password.message}
              </p>
            )}
          </div>

          {/* Submit Button */}
          <Button type="submit" className="w-full" disabled={isLoggingIn}>
            {isLoggingIn ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing in...
              </>
            ) : (
              'Sign In'
            )}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="flex flex-col space-y-2">
        <p className="text-sm text-muted-foreground">
          Don't have an account?{' '}
          {onSwitchToRegister ? (
            <button
              type="button"
              onClick={onSwitchToRegister}
              className="text-primary underline-offset-4 hover:underline"
            >
              Sign up
            </button>
          ) : (
            <Link
              to="/register"
              className="text-primary underline-offset-4 hover:underline"
            >
              Sign up
            </Link>
          )}
        </p>
      </CardFooter>
    </Card>
  );
}

export default LoginForm;