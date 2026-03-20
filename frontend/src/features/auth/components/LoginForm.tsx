/**
 * LoginForm Component — Professional & Industrial Grade
 *
 * Enhanced login form with Remember Me, role-based welcome message,
 * security-conscious error handling, and glassmorphism styling.
 */

import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  LogIn,
  Mail,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { FormField } from "@/components/ui/form-field";
import { GlassCard } from "@/components/ui/glass-card";
import { Label } from "@/components/ui/label";

import { useAuthStore } from "@/state/stores/authStore";
import { useAuth } from "../hooks/useAuth";
import { CityStatusBadge } from "./CityStatusBadge";

const loginSchema = z.object({
  email: z
    .string()
    .min(1, "Email is required")
    .email("Please enter a valid email address"),
  password: z
    .string()
    .min(1, "Password is required")
    .min(8, "Password must be at least 8 characters"),
});

type LoginFormData = z.infer<typeof loginSchema>;

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

/** Map user role to display name and redirect path */
const ROLE_CONFIG: Record<string, { label: string; path: string }> = {
  admin: { label: "Admin", path: "/admin" },
  operator: { label: "LGU Operator", path: "/operator" },
  user: { label: "Resident", path: "/resident" },
};

/** Parse API error into a user-friendly message (security-conscious) */
function getLoginErrorMessage(error: unknown): string {
  const msg = (error as { message?: string; code?: string })?.message ?? "";
  const code = (error as { code?: string })?.code ?? "";

  if (code === "ACCOUNT_SUSPENDED" || msg.toLowerCase().includes("suspend")) {
    return "Your account has been suspended. Please contact the system administrator.";
  }
  if (code === "ACCOUNT_UNVERIFIED" || msg.toLowerCase().includes("verif")) {
    return "Please verify your email address before signing in.";
  }
  if (code === "RATE_LIMITED" || msg.toLowerCase().includes("too many")) {
    return "Too many failed attempts. Please try again in a few minutes.";
  }
  return "Incorrect email or password. Please try again.";
}

interface LoginFormProps {
  onSwitchToRegister?: () => void;
}

export function LoginForm({ onSwitchToRegister }: LoginFormProps = {}) {
  const { login, isLoggingIn, loginError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const welcomeRole =
    isAuthenticated && user
      ? ((ROLE_CONFIG[user.role] ?? ROLE_CONFIG.user)?.label ?? null)
      : null;

  useEffect(() => {
    if (isAuthenticated && user) {
      const config = ROLE_CONFIG[user.role] ?? ROLE_CONFIG.user;

      const from = (location.state as { from?: { pathname: string } })?.from
        ?.pathname;
      const destination = from ?? config?.path ?? "/dashboard";

      const timer = setTimeout(() => {
        navigate(destination, { replace: true });
      }, 1500);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [isAuthenticated, user, navigate, location.state]);

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
    defaultValues: { email: "", password: "" },
    mode: "onBlur",
  });

  const { ref: emailRegRef, ...emailRegRest } = register("email");

  const onSubmit = useCallback(
    (data: LoginFormData) => {
      login(data);
    },
    [login],
  );

  const errorMessage = loginError ? getLoginErrorMessage(loginError) : null;

  // Welcome message briefly shown before redirect
  if (welcomeRole) {
    return (
      <GlassCard intensity="medium" className="w-full overflow-hidden">
        <div className="h-1 w-full bg-linear-to-r from-risk-safe/80 via-risk-safe to-risk-safe/80" />
        <motion.div
          className="flex flex-col items-center text-center p-8 space-y-4"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, type: "spring" }}
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-risk-safe/15 ring-4 ring-risk-safe/10">
            <LogIn className="h-6 w-6 text-risk-safe" />
          </div>
          <div>
            <h2 className="text-xl font-bold">Welcome back, {welcomeRole}</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Redirecting to your dashboard...
            </p>
          </div>
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        </motion.div>
      </GlassCard>
    );
  }

  return (
    <GlassCard intensity="medium" className="w-full overflow-hidden">
      <div className="h-1 w-full bg-linear-to-r from-primary/80 via-primary to-primary/80" />

      <div className="p-6 pb-2 space-y-1.5">
        {/* Mobile-only city status */}
        <div className="flex justify-center lg:hidden mb-3">
          <CityStatusBadge />
        </div>
        <h2 className="text-2xl font-bold tracking-tight">Welcome back</h2>
        <p className="text-sm text-muted-foreground">
          Enter your credentials to access your account
        </p>
      </div>

      <div className="px-6 pb-6">
        <motion.form
          onSubmit={handleSubmit(onSubmit)}
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="space-y-4"
          noValidate
        >
          {/* Error Alert */}
          <AnimatePresence>
            {errorMessage && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95, height: 0 }}
                animate={{ opacity: 1, scale: 1, height: "auto" }}
                exit={{ opacity: 0, scale: 0.95, height: 0 }}
                transition={{ duration: 0.25 }}
              >
                <Alert
                  variant="destructive"
                  role="alert"
                  aria-live="assertive"
                  className="border-destructive/30 bg-destructive/10"
                >
                  <AlertCircle className="h-4 w-4" aria-hidden="true" />
                  <AlertDescription>{errorMessage}</AlertDescription>
                </Alert>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Email */}
          <motion.div variants={itemVariants}>
            <FormField
              id="login-email"
              label="Email Address"
              icon={Mail}
              type="email"
              placeholder="name@example.com"
              autoComplete="email"
              disabled={isLoggingIn}
              error={errors.email?.message}
              {...emailRegRest}
              ref={(e) => {
                emailRegRef(e);
                emailRef.current = e;
              }}
            />
          </motion.div>

          {/* Password */}
          <motion.div variants={itemVariants}>
            <FormField
              id="login-password"
              label="Password"
              icon={Lock}
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              autoComplete="current-password"
              disabled={isLoggingIn}
              error={errors.password?.message}
              {...register("password")}
              trailing={
                <button
                  type="button"
                  className="text-muted-foreground/60 hover:text-foreground transition-colors duration-200"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              }
            />
          </motion.div>

          {/* Remember Me + Forgot Password */}
          <motion.div
            variants={itemVariants}
            className="flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <Checkbox
                id="remember-me"
                checked={rememberMe}
                onCheckedChange={(checked) => setRememberMe(checked === true)}
                aria-label="Remember me for 30 days"
              />
              <Label
                htmlFor="remember-me"
                className="text-sm text-muted-foreground cursor-pointer select-none"
              >
                Remember me
              </Label>
            </div>
            <Link
              to="/forgot-password"
              className="text-xs text-muted-foreground hover:text-primary transition-colors duration-200 underline-offset-4 hover:underline"
            >
              Forgot password?
            </Link>
          </motion.div>

          {/* Submit */}
          <motion.div variants={itemVariants}>
            <Button
              type="submit"
              className="w-full h-11 rounded-xl bg-linear-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all duration-300"
              disabled={isLoggingIn}
            >
              {isLoggingIn ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  <LogIn className="mr-2 h-4 w-4" />
                  Sign In
                </>
              )}
            </Button>
          </motion.div>

          {/* Public device notice */}
          <motion.p
            variants={itemVariants}
            className="text-[11px] text-muted-foreground/50 text-center"
          >
            Using a public or shared device? Uncheck &quot;Remember me&quot; and
            sign out when finished.
          </motion.p>
        </motion.form>
      </div>

      {/* Footer */}
      <div className="px-6 pb-6 flex flex-col items-center space-y-2">
        <div className="w-full h-px bg-linear-to-r from-transparent via-border/50 to-transparent" />
        <p className="text-sm text-muted-foreground pt-2">
          Don&apos;t have an account?{" "}
          {onSwitchToRegister ? (
            <button
              type="button"
              onClick={onSwitchToRegister}
              className="text-primary font-medium underline-offset-4 hover:underline transition-colors"
            >
              Sign up
            </button>
          ) : (
            <Link
              to="/register"
              className="text-primary font-medium underline-offset-4 hover:underline transition-colors"
            >
              Sign up
            </Link>
          )}
        </p>
      </div>
    </GlassCard>
  );
}

export default LoginForm;
