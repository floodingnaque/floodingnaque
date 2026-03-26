/**
 * RegisterForm Component - Web 3.0 Edition
 *
 * Glass-morphism registration form with animated fields, icon-enhanced inputs,
 * password strength meter, gradient accents, and smooth micro-interactions.
 * Uses react-hook-form with zod validation.
 */

import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  Mail,
  User,
  UserPlus,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { GlassCard } from "@/components/ui/glass-card";
import { PasswordStrengthMeter } from "@/components/ui/password-strength-meter";

import { useAuth } from "../hooks/useAuth";

/**
 * Register form validation schema
 */
const registerSchema = z.object({
  name: z
    .string()
    .min(1, "Name is required")
    .min(2, "Name must be at least 2 characters"),
  email: z
    .string()
    .min(1, "Email is required")
    .email("Please enter a valid email address"),
  password: z
    .string()
    .min(1, "Password is required")
    .min(12, "Password must be at least 12 characters")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/[a-z]/, "Password must contain at least one lowercase letter")
    .regex(/[0-9]/, "Password must contain at least one digit")
    .regex(
      /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/,
      "Password must contain at least one special character",
    ),
});

type RegisterFormData = z.infer<typeof registerSchema>;

/** Stagger children entrance animation */
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

/**
 * RegisterForm component props
 */
interface RegisterFormProps {
  /** Callback when switching to login tab */
  onSwitchToLogin?: () => void;
}

/**
 * RegisterForm renders a modern glass-morphism registration form with validation
 */
export function RegisterForm({ onSwitchToLogin }: RegisterFormProps) {
  const { register: registerUser, isRegistering, registerError } = useAuth();

  // Auto-focus first field on mount
  const nameRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
    },
  });

  const [showPassword, setShowPassword] = useState(false);
  const passwordValue = useWatch({ control, name: "password" });

  // Combine react-hook-form ref with our focus ref
  const { ref: nameRegRef, ...nameRegRest } = register("name");

  const onSubmit = (data: RegisterFormData) => {
    registerUser(data);
  };

  // Extract error message from registerError
  const errorMessage = registerError
    ? (registerError as { message?: string }).message ||
      "Registration failed. Please try again."
    : null;

  return (
    <GlassCard intensity="medium" className="w-full overflow-hidden">
      {/* Decorative gradient accent bar */}
      <div className="h-1 w-full bg-linear-to-r from-primary/80 via-primary to-primary/80" />

      <div className="p-6 pb-2 space-y-1.5">
        <h2 className="text-2xl font-bold tracking-tight">Create an account</h2>
        <p className="text-sm text-muted-foreground">
          Enter your details to create your account
        </p>
      </div>

      <div className="px-6 pb-6">
        <motion.form
          onSubmit={handleSubmit(onSubmit)}
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="space-y-4"
        >
          {/* API Error Alert */}
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

          {/* Name Field */}
          <motion.div variants={itemVariants}>
            <FormField
              id="register-name"
              label="Full Name"
              icon={User}
              type="text"
              placeholder="John Doe"
              autoComplete="name"
              disabled={isRegistering}
              error={errors.name?.message}
              {...nameRegRest}
              ref={(e) => {
                nameRegRef(e);
                nameRef.current = e;
              }}
            />
          </motion.div>

          {/* Email Field */}
          <motion.div variants={itemVariants}>
            <FormField
              id="register-email"
              label="Email"
              icon={Mail}
              type="email"
              placeholder="name@example.com"
              autoComplete="email"
              disabled={isRegistering}
              error={errors.email?.message}
              {...register("email")}
            />
          </motion.div>

          {/* Password Field */}
          <motion.div variants={itemVariants}>
            <FormField
              id="register-password"
              label="Password"
              icon={Lock}
              type={showPassword ? "text" : "password"}
              placeholder="Create a strong password"
              autoComplete="new-password"
              disabled={isRegistering}
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
            {/* Password Strength Meter */}
            <div className="mt-2">
              <PasswordStrengthMeter password={passwordValue || ""} />
            </div>
          </motion.div>

          {/* Submit Button */}
          <motion.div variants={itemVariants}>
            <Button
              type="submit"
              className="w-full h-11 rounded-xl bg-linear-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all duration-300"
              disabled={isRegistering}
            >
              {isRegistering ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                <>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Create Account
                </>
              )}
            </Button>
          </motion.div>
        </motion.form>
      </div>

      {/* Footer */}
      <div className="px-6 pb-6 flex flex-col items-center space-y-2">
        <div className="w-full h-px bg-linear-to-r from-transparent via-border/50 to-transparent" />
        <p className="text-sm text-muted-foreground pt-2">
          Already have an account?{" "}
          {onSwitchToLogin ? (
            <button
              type="button"
              onClick={onSwitchToLogin}
              className="text-primary font-medium underline-offset-4 hover:underline transition-colors"
            >
              Sign in
            </button>
          ) : (
            <Link
              to="/login"
              className="text-primary font-medium underline-offset-4 hover:underline transition-colors"
            >
              Sign in
            </Link>
          )}
        </p>
      </div>
    </GlassCard>
  );
}

export default RegisterForm;
