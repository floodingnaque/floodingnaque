/**
 * ForgotPasswordForm - 3-State Password Reset Flow
 *
 * State 1: Request Reset - email input with security-conscious messaging
 * State 2: Email Sent Confirmation - resend with 60s cooldown timer
 * State 3: Reset Password - new password form (accessed via URL token)
 *
 * Auto-detects State 3 when `?token=...&email=...` query params are present.
 */

import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Eye,
  EyeOff,
  Info,
  KeyRound,
  Loader2,
  Lock,
  Mail,
  Send,
  ShieldCheck,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { GlassCard } from "@/components/ui/glass-card";
import { PasswordStrengthMeter } from "@/components/ui/password-strength-meter";

import { useAuth } from "../hooks/useAuth";
import { PasswordRequirements } from "./PasswordRequirements";

/* ------------------------------------------------------------------ */
/*  Schemas                                                            */
/* ------------------------------------------------------------------ */

const requestSchema = z.object({
  email: z.string().min(1, "Email is required").email("Invalid email address"),
});
type RequestFormData = z.infer<typeof requestSchema>;

const resetSchema = z
  .object({
    newPassword: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must contain an uppercase letter")
      .regex(/[a-z]/, "Must contain a lowercase letter")
      .regex(/[0-9]/, "Must contain a number")
      .regex(
        /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/,
        "Must contain a special character",
      ),
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });
type ResetFormData = z.infer<typeof resetSchema>;

/* ------------------------------------------------------------------ */
/*  Animation variants                                                 */
/* ------------------------------------------------------------------ */

const slideVariants = {
  enter: { opacity: 0, x: 30 },
  center: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -30 },
};

const containerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: "easeOut" as const },
  },
} as const;

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type FlowState = "request" | "confirmation" | "reset";

const RESEND_COOLDOWN_SECONDS = 60;
const REDIRECT_DELAY_MS = 3000;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ForgotPasswordForm() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const {
    requestPasswordReset,
    isRequestingPasswordReset,
    requestPasswordResetError,
    confirmPasswordReset,
    isConfirmingPasswordReset,
    confirmPasswordResetError,
  } = useAuth();

  // Detect token/email in URL for direct reset link
  const urlToken = searchParams.get("token");
  const urlEmail = searchParams.get("email");

  // Determine initial state based on URL params
  const initialState: FlowState = useMemo(
    () => (urlToken && urlEmail ? "reset" : "request"),
    [urlToken, urlEmail],
  );

  const [flowState, setFlowState] = useState<FlowState>(initialState);
  const [submittedEmail, setSubmittedEmail] = useState(urlEmail ?? "");
  const [resetComplete, setResetComplete] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [devTokenNotice, setDevTokenNotice] = useState("");

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Auto-redirect after successful reset
  useEffect(() => {
    if (!resetComplete) return;
    const timer = setTimeout(() => {
      navigate("/login", { replace: true });
    }, REDIRECT_DELAY_MS);
    return () => clearTimeout(timer);
  }, [resetComplete, navigate]);

  /* -- State 1: Request form -------------------------------------- */

  const requestForm = useForm<RequestFormData>({
    resolver: zodResolver(requestSchema),
    defaultValues: { email: "" },
    mode: "onBlur",
  });

  const handleRequestSubmit = useCallback(
    (data: RequestFormData) => {
      requestPasswordReset(data, {
        onSuccess: (result) => {
          setSubmittedEmail(data.email);
          setFlowState("confirmation");
          setResendCooldown(RESEND_COOLDOWN_SECONDS);

          // Dev mode: SMTP not configured, token returned directly
          if (result?.dev_token) {
            setDevTokenNotice(result.dev_token);
            toast.info("Development mode", {
              description: "SMTP not configured - token shown below.",
            });
          }
        },
        onError: () => {
          // Security: always show success message to prevent email enumeration
          setSubmittedEmail(data.email);
          setFlowState("confirmation");
          setResendCooldown(RESEND_COOLDOWN_SECONDS);
        },
      });
    },
    [requestPasswordReset],
  );

  const handleResend = useCallback(() => {
    if (resendCooldown > 0 || !submittedEmail) return;
    requestPasswordReset(
      { email: submittedEmail },
      {
        onSuccess: () => {
          setResendCooldown(RESEND_COOLDOWN_SECONDS);
          toast.success("Email sent", {
            description: "A new reset link has been sent to your email.",
          });
        },
      },
    );
  }, [resendCooldown, submittedEmail, requestPasswordReset]);

  /* -- State 3: Reset form ---------------------------------------- */

  const resetForm = useForm<ResetFormData>({
    resolver: zodResolver(resetSchema),
    defaultValues: { newPassword: "", confirmPassword: "" },
    mode: "onBlur",
  });

  const newPasswordValue = useWatch({
    control: resetForm.control,
    name: "newPassword",
  });

  const handleResetSubmit = useCallback(
    (data: ResetFormData) => {
      const email = urlEmail ?? submittedEmail;
      const token = urlToken ?? "";

      if (!email || !token) {
        toast.error("Invalid reset link", {
          description: "Please request a new password reset.",
        });
        return;
      }

      confirmPasswordReset(
        { email, token, new_password: data.newPassword },
        {
          onSuccess: () => {
            setResetComplete(true);
            toast.success("Password reset successful", {
              description: "Redirecting to sign in...",
            });
          },
        },
      );
    },
    [confirmPasswordReset, urlEmail, urlToken, submittedEmail],
  );

  const requestErrorMsg = requestPasswordResetError
    ? (requestPasswordResetError as { message?: string }).message ||
      "Something went wrong. Please try again."
    : null;

  const resetErrorMsg = confirmPasswordResetError
    ? (confirmPasswordResetError as { message?: string }).message ||
      "Reset failed. The link may have expired. Please request a new one."
    : null;

  /* ================================================================ */
  /*  SUCCESS VIEW                                                     */
  /* ================================================================ */

  if (resetComplete) {
    return (
      <GlassCard intensity="medium" className="w-full overflow-hidden">
        <div className="h-1 w-full bg-linear-to-r from-risk-safe/80 via-risk-safe to-risk-safe/80" />
        <motion.div
          className="flex flex-col items-center text-center p-8 space-y-5"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, type: "spring" }}
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-risk-safe/15 ring-4 ring-risk-safe/10">
            <CheckCircle2 className="h-8 w-8 text-risk-safe" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold tracking-tight">
              Password Reset Complete
            </h2>
            <p className="text-sm text-muted-foreground max-w-xs">
              Your password has been changed successfully. You will be
              redirected to sign in shortly.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground/60">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Redirecting in a few seconds...
          </div>
          <Link to="/login" className="w-full">
            <Button variant="outline" className="w-full h-11 rounded-xl">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Go to Sign In Now
            </Button>
          </Link>
        </motion.div>
      </GlassCard>
    );
  }

  /* ================================================================ */
  /*  STATE 1: REQUEST RESET                                           */
  /* ================================================================ */

  if (flowState === "request") {
    return (
      <GlassCard intensity="medium" className="w-full overflow-hidden">
        <div className="h-1 w-full bg-linear-to-r from-primary/80 via-primary to-primary/80" />

        <div className="p-6 space-y-5">
          <AnimatePresence mode="wait">
            <motion.div
              key="request"
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.25 }}
              className="space-y-4"
            >
              {/* Header */}
              <div className="space-y-1.5">
                <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                  <KeyRound className="h-5 w-5 text-primary" />
                  Forgot Password
                </h2>
                <p className="text-sm text-muted-foreground">
                  Enter your email and we&apos;ll send you a link to reset your
                  password.
                </p>
              </div>

              {/* Form */}
              <motion.form
                onSubmit={requestForm.handleSubmit(handleRequestSubmit)}
                variants={containerVariants}
                initial="hidden"
                animate="show"
                className="space-y-4"
                noValidate
              >
                <AnimatePresence>
                  {requestErrorMsg && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.25 }}
                    >
                      <Alert
                        variant="destructive"
                        role="alert"
                        aria-live="assertive"
                        className="border-destructive/30 bg-destructive/10"
                      >
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{requestErrorMsg}</AlertDescription>
                      </Alert>
                    </motion.div>
                  )}
                </AnimatePresence>

                <motion.div variants={itemVariants}>
                  <FormField
                    id="reset-email"
                    label="Email Address"
                    icon={Mail}
                    type="email"
                    placeholder="name@example.com"
                    autoComplete="email"
                    disabled={isRequestingPasswordReset}
                    error={requestForm.formState.errors.email?.message}
                    {...requestForm.register("email")}
                  />
                </motion.div>

                <motion.div variants={itemVariants}>
                  <Button
                    type="submit"
                    className="w-full h-11 rounded-xl bg-linear-to-r from-primary to-primary/90 shadow-lg shadow-primary/20 transition-all duration-300"
                    disabled={isRequestingPasswordReset}
                  >
                    {isRequestingPasswordReset ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <Send className="mr-2 h-4 w-4" />
                        Send Reset Link
                      </>
                    )}
                  </Button>
                </motion.div>

                {/* Security notice */}
                <motion.div
                  variants={itemVariants}
                  className="flex items-start gap-2 p-3 rounded-lg bg-muted/30 border border-border/40"
                >
                  <ShieldCheck className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    For security, we&apos;ll send a reset link if an account
                    exists with this email. Reset links expire after 30 minutes.
                  </p>
                </motion.div>
              </motion.form>

              {/* Footer */}
              <div className="w-full h-px bg-linear-to-r from-transparent via-border/50 to-transparent" />
              <p className="text-sm text-muted-foreground text-center">
                Remember your password?{" "}
                <Link
                  to="/login"
                  className="text-primary font-medium underline-offset-4 hover:underline transition-colors"
                >
                  Sign in
                </Link>
              </p>
            </motion.div>
          </AnimatePresence>
        </div>
      </GlassCard>
    );
  }

  /* ================================================================ */
  /*  STATE 2: EMAIL SENT CONFIRMATION                                 */
  /* ================================================================ */

  if (flowState === "confirmation") {
    return (
      <GlassCard intensity="medium" className="w-full overflow-hidden">
        <div className="h-1 w-full bg-linear-to-r from-primary/80 via-primary to-primary/80" />

        <div className="p-6 space-y-5">
          <AnimatePresence mode="wait">
            <motion.div
              key="confirmation"
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.25 }}
              className="space-y-5"
            >
              {/* Email icon */}
              <motion.div
                className="flex flex-col items-center text-center space-y-3"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 }}
              >
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 ring-4 ring-primary/5">
                  <Mail className="h-8 w-8 text-primary" />
                </div>
                <div className="space-y-1.5">
                  <h2 className="text-2xl font-bold tracking-tight">
                    Check Your Email
                  </h2>
                  <p className="text-sm text-muted-foreground max-w-sm">
                    If an account exists for{" "}
                    <span className="font-medium text-foreground">
                      {submittedEmail}
                    </span>
                    , we&apos;ve sent a password reset link.
                  </p>
                </div>
              </motion.div>

              {/* Instructions */}
              <div className="space-y-3 p-4 rounded-lg bg-muted/20 border border-border/30">
                <h3 className="text-sm font-medium">What to do next:</h3>
                <ol className="space-y-2 text-xs text-muted-foreground list-decimal list-inside">
                  <li>Check your inbox (and spam folder)</li>
                  <li>Click the reset link in the email</li>
                  <li>Choose a new secure password</li>
                </ol>
                <div className="flex items-center gap-2 text-xs text-muted-foreground/60 pt-1">
                  <Clock className="h-3.5 w-3.5" />
                  Reset links expire after 30 minutes
                </div>
              </div>

              {/* Dev token notice */}
              {devTokenNotice && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20"
                >
                  <div className="flex items-start gap-2">
                    <Info className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-amber-500">
                        Development Mode - SMTP Not Configured
                      </p>
                      <p className="text-xs text-muted-foreground font-mono break-all">
                        Token: {devTokenNotice}
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Resend button with cooldown */}
              <div className="flex flex-col items-center space-y-3">
                <Button
                  variant="outline"
                  className="w-full h-11 rounded-xl"
                  disabled={resendCooldown > 0 || isRequestingPasswordReset}
                  onClick={handleResend}
                >
                  {isRequestingPasswordReset ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Sending...
                    </>
                  ) : resendCooldown > 0 ? (
                    <>
                      <Clock className="mr-2 h-4 w-4" />
                      Resend in {resendCooldown}s
                    </>
                  ) : (
                    <>
                      <Send className="mr-2 h-4 w-4" />
                      Resend Reset Link
                    </>
                  )}
                </Button>

                <button
                  type="button"
                  onClick={() => {
                    setFlowState("request");
                    requestForm.reset();
                  }}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Use a different email address
                </button>
              </div>

              {/* Footer */}
              <div className="w-full h-px bg-linear-to-r from-transparent via-border/50 to-transparent" />
              <p className="text-sm text-muted-foreground text-center">
                <Link
                  to="/login"
                  className="text-primary font-medium underline-offset-4 hover:underline transition-colors inline-flex items-center gap-1"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back to Sign In
                </Link>
              </p>
            </motion.div>
          </AnimatePresence>
        </div>
      </GlassCard>
    );
  }

  /* ================================================================ */
  /*  STATE 3: RESET PASSWORD FORM                                     */
  /* ================================================================ */

  return (
    <GlassCard intensity="medium" className="w-full overflow-hidden">
      <div className="h-1 w-full bg-linear-to-r from-primary/80 via-primary to-primary/80" />

      <div className="p-6 space-y-5">
        <AnimatePresence mode="wait">
          <motion.div
            key="reset"
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.25 }}
            className="space-y-4"
          >
            {/* Header */}
            <div className="space-y-1.5">
              <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                <Lock className="h-5 w-5 text-primary" />
                Set New Password
              </h2>
              <p className="text-sm text-muted-foreground">
                Choose a strong password for your account.
              </p>
            </div>

            {/* Reset form */}
            <motion.form
              onSubmit={resetForm.handleSubmit(handleResetSubmit)}
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="space-y-4"
              noValidate
            >
              <AnimatePresence>
                {resetErrorMsg && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25 }}
                  >
                    <Alert
                      variant="destructive"
                      role="alert"
                      aria-live="assertive"
                      className="border-destructive/30 bg-destructive/10"
                    >
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{resetErrorMsg}</AlertDescription>
                    </Alert>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* New password */}
              <motion.div variants={itemVariants}>
                <FormField
                  id="new-password"
                  label="New Password"
                  icon={Lock}
                  type={showNewPassword ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="Choose a strong password"
                  disabled={isConfirmingPasswordReset}
                  error={resetForm.formState.errors.newPassword?.message}
                  {...resetForm.register("newPassword")}
                  trailing={
                    <button
                      type="button"
                      className="text-muted-foreground/60 hover:text-foreground transition-colors duration-200"
                      onClick={() => setShowNewPassword((v) => !v)}
                      aria-label={
                        showNewPassword ? "Hide password" : "Show password"
                      }
                      tabIndex={-1}
                    >
                      {showNewPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  }
                />
                <div className="mt-2">
                  <PasswordStrengthMeter password={newPasswordValue || ""} />
                </div>
                <PasswordRequirements password={newPasswordValue || ""} />
              </motion.div>

              {/* Confirm password */}
              <motion.div variants={itemVariants}>
                <FormField
                  id="confirm-password"
                  label="Confirm Password"
                  icon={Lock}
                  type={showConfirmPassword ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="Confirm your new password"
                  disabled={isConfirmingPasswordReset}
                  error={resetForm.formState.errors.confirmPassword?.message}
                  {...resetForm.register("confirmPassword")}
                  trailing={
                    <button
                      type="button"
                      className="text-muted-foreground/60 hover:text-foreground transition-colors duration-200"
                      onClick={() => setShowConfirmPassword((v) => !v)}
                      aria-label={
                        showConfirmPassword ? "Hide password" : "Show password"
                      }
                      tabIndex={-1}
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  }
                />
              </motion.div>

              {/* Submit */}
              <motion.div variants={itemVariants}>
                <Button
                  type="submit"
                  className="w-full h-11 rounded-xl bg-linear-to-r from-primary to-primary/90 shadow-lg shadow-primary/20 transition-all duration-300"
                  disabled={isConfirmingPasswordReset}
                >
                  {isConfirmingPasswordReset ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Resetting...
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="mr-2 h-4 w-4" />
                      Reset Password
                    </>
                  )}
                </Button>
              </motion.div>
            </motion.form>

            {/* Footer */}
            <div className="w-full h-px bg-linear-to-r from-transparent via-border/50 to-transparent" />
            <p className="text-sm text-muted-foreground text-center">
              <Link
                to="/login"
                className="text-primary font-medium underline-offset-4 hover:underline transition-colors inline-flex items-center gap-1"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to Sign In
              </Link>
            </p>
          </motion.div>
        </AnimatePresence>
      </div>
    </GlassCard>
  );
}

export default ForgotPasswordForm;
