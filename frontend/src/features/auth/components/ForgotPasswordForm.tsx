/**
 * ForgotPasswordForm Component
 *
 * Two-step password reset form:
 * 1. Request reset - user enters email to receive a reset token
 * 2. Confirm reset - user enters email, token, and new password
 */

import { useState, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AlertCircle, Loader2, ArrowLeft, Mail, KeyRound } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

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

/* ------------------------------------------------------------------ */
/*  Step 1 - Request Reset                                             */
/* ------------------------------------------------------------------ */

const requestSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Invalid email address'),
});
type RequestFormData = z.infer<typeof requestSchema>;

/* ------------------------------------------------------------------ */
/*  Step 2 - Confirm Reset                                             */
/* ------------------------------------------------------------------ */

const confirmSchema = z
  .object({
    email: z.string().min(1, 'Email is required').email('Invalid email address'),
    token: z.string().min(1, 'Reset token is required'),
    newPassword: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });
type ConfirmFormData = z.infer<typeof confirmSchema>;

/**
 * ForgotPasswordForm renders a two-step password reset flow
 */
export function ForgotPasswordForm() {
  const {
    requestPasswordReset,
    isRequestingPasswordReset,
    requestPasswordResetError,
    confirmPasswordReset,
    isConfirmingPasswordReset,
    confirmPasswordResetError,
  } = useAuth();

  const [step, setStep] = useState<'request' | 'confirm'>('request');
  const [submittedEmail, setSubmittedEmail] = useState('');
  const [resetComplete, setResetComplete] = useState(false);

  /* -- Step 1 form ------------------------------------------------- */

  const requestForm = useForm<RequestFormData>({
    resolver: zodResolver(requestSchema),
    defaultValues: { email: '' },
  });

  const handleRequestSubmit = useCallback(
    (data: RequestFormData) => {
      requestPasswordReset(data, {
        onSuccess: () => {
          setSubmittedEmail(data.email);
          setStep('confirm');
          toast.success('Reset email sent', {
            description: 'Check your inbox for the reset token.',
          });
        },
      });
    },
    [requestPasswordReset],
  );

  /* -- Step 2 form ------------------------------------------------- */

  const confirmForm = useForm<ConfirmFormData>({
    resolver: zodResolver(confirmSchema),
    defaultValues: {
      email: submittedEmail,
      token: '',
      newPassword: '',
      confirmPassword: '',
    },
  });

  // Keep email in sync when moving to step 2
  if (step === 'confirm' && confirmForm.getValues('email') !== submittedEmail) {
    confirmForm.setValue('email', submittedEmail);
  }

  const handleConfirmSubmit = useCallback(
    (data: ConfirmFormData) => {
      confirmPasswordReset(
        {
          email: data.email,
          token: data.token,
          new_password: data.newPassword,
        },
        {
          onSuccess: () => {
            setResetComplete(true);
            toast.success('Password reset successful', {
              description: 'You can now sign in with your new password.',
            });
          },
        },
      );
    },
    [confirmPasswordReset],
  );

  /* -- Success view ------------------------------------------------ */

  if (resetComplete) {
    return (
      <Card className="w-full">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-2xl font-bold">Password Reset</CardTitle>
          <CardDescription>
            Your password has been changed successfully.
          </CardDescription>
        </CardHeader>
        <CardFooter className="flex justify-center">
          <Link to="/login">
            <Button>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Sign In
            </Button>
          </Link>
        </CardFooter>
      </Card>
    );
  }

  /* -- Step 1 view ------------------------------------------------- */

  if (step === 'request') {
    const errorMsg = requestPasswordResetError
      ? (requestPasswordResetError as { message?: string }).message ||
        'Something went wrong. Please try again.'
      : null;

    return (
      <Card className="w-full">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Forgot Password
          </CardTitle>
          <CardDescription>
            Enter your email address and we'll send you a reset token.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={requestForm.handleSubmit(handleRequestSubmit)}
            className="space-y-4"
          >
            {errorMsg && (
              <Alert variant="destructive" role="alert">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{errorMsg}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="reset-email">Email</Label>
              <Input
                id="reset-email"
                type="email"
                placeholder="name@example.com"
                autoComplete="email"
                disabled={isRequestingPasswordReset}
                {...requestForm.register('email')}
              />
              {requestForm.formState.errors.email && (
                <p className="text-sm text-destructive">
                  {requestForm.formState.errors.email.message}
                </p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={isRequestingPasswordReset}
            >
              {isRequestingPasswordReset ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Sending...
                </>
              ) : (
                'Send Reset Token'
              )}
            </Button>
          </form>
        </CardContent>
        <CardFooter>
          <p className="text-sm text-muted-foreground">
            Remember your password?{' '}
            <Link
              to="/login"
              className="text-primary underline-offset-4 hover:underline"
            >
              Sign in
            </Link>
          </p>
        </CardFooter>
      </Card>
    );
  }

  /* -- Step 2 view ------------------------------------------------- */

  const confirmErrorMsg = confirmPasswordResetError
    ? (confirmPasswordResetError as { message?: string }).message ||
      'Reset failed. Please check your token and try again.'
    : null;

  return (
    <Card className="w-full">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold flex items-center gap-2">
          <KeyRound className="h-5 w-5" />
          Reset Password
        </CardTitle>
        <CardDescription>
          Enter the token from your email and choose a new password.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={confirmForm.handleSubmit(handleConfirmSubmit)}
          className="space-y-4"
        >
          {confirmErrorMsg && (
            <Alert variant="destructive" role="alert">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{confirmErrorMsg}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="confirm-email">Email</Label>
            <Input
              id="confirm-email"
              type="email"
              disabled={isConfirmingPasswordReset}
              {...confirmForm.register('email')}
            />
            {confirmForm.formState.errors.email && (
              <p className="text-sm text-destructive">
                {confirmForm.formState.errors.email.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="reset-token">Reset Token</Label>
            <Input
              id="reset-token"
              placeholder="Paste the token from your email"
              disabled={isConfirmingPasswordReset}
              {...confirmForm.register('token')}
            />
            {confirmForm.formState.errors.token && (
              <p className="text-sm text-destructive">
                {confirmForm.formState.errors.token.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="new-password">New Password</Label>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              disabled={isConfirmingPasswordReset}
              {...confirmForm.register('newPassword')}
            />
            {confirmForm.formState.errors.newPassword && (
              <p className="text-sm text-destructive">
                {confirmForm.formState.errors.newPassword.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm-password">Confirm Password</Label>
            <Input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              disabled={isConfirmingPasswordReset}
              {...confirmForm.register('confirmPassword')}
            />
            {confirmForm.formState.errors.confirmPassword && (
              <p className="text-sm text-destructive">
                {confirmForm.formState.errors.confirmPassword.message}
              </p>
            )}
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={isConfirmingPasswordReset}
          >
            {isConfirmingPasswordReset ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Resetting...
              </>
            ) : (
              'Reset Password'
            )}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="flex flex-col space-y-2">
        <button
          type="button"
          onClick={() => setStep('request')}
          className="text-sm text-muted-foreground hover:underline"
        >
          Didn't receive a token? Resend
        </button>
        <p className="text-sm text-muted-foreground">
          <Link
            to="/login"
            className="text-primary underline-offset-4 hover:underline"
          >
            Back to Sign In
          </Link>
        </p>
      </CardFooter>
    </Card>
  );
}

export default ForgotPasswordForm;
