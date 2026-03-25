/**
 * RegistrationWizard — Multi-step resident onboarding form
 *
 * 4-step registration process:
 *   Step 1: Account Information (name, email, password)
 *   Step 2: Personal & Household Information
 *   Step 3: Address, Location & Notification Preferences
 *   Step 4: Review & Submit
 *
 * Uses react-hook-form with Zod validation per step.
 * Navigation: Next/Back between steps, final summary before submission.
 */

import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  Home,
  Loader2,
  Lock,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Shield,
  User,
  UserPlus,
  Users,
} from "lucide-react";
import { useCallback, useState } from "react";
import {
  Controller,
  useForm,
  useWatch,
  type Resolver,
  type UseFormReturn,
} from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { FormField } from "@/components/ui/form-field";
import { GlassCard } from "@/components/ui/glass-card";
import { Label } from "@/components/ui/label";
import { PasswordStrengthMeter } from "@/components/ui/password-strength-meter";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StepIndicator } from "@/components/ui/step-indicator";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

import {
  ALERT_LANGUAGE_OPTIONS,
  BARANGAY_NAMES,
  CIVIL_STATUS_OPTIONS,
  FLOOR_LEVEL_OPTIONS,
  getBarangayInfo,
  HOME_TYPE_OPTIONS,
  SEX_OPTIONS,
} from "../constants/paranaque-data";
import { useAuth } from "../hooks/useAuth";
import { CityStatusBadge } from "./CityStatusBadge";
import { PasswordRequirements } from "./PasswordRequirements";

/* ================================================================== */
/*  Validation Schemas                                                 */
/* ================================================================== */

const step1Schema = z
  .object({
    full_name: z
      .string()
      .min(1, "Full name is required")
      .min(3, "Must be at least 3 characters")
      .regex(/^[a-zA-Z\s.\-'ñÑ]+$/, "No special characters allowed"),
    email: z
      .string()
      .min(1, "Email is required")
      .email("Please enter a valid email address"),
    password: z
      .string()
      .min(1, "Password is required")
      .min(8, "Must be at least 8 characters")
      .regex(/[A-Z]/, "Needs an uppercase letter")
      .regex(/[a-z]/, "Needs a lowercase letter")
      .regex(/[0-9]/, "Needs a number")
      .regex(/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/, "Needs a special character"),
    confirm_password: z.string().min(1, "Please confirm your password"),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

const step2Schema = z.object({
  date_of_birth: z
    .string()
    .min(1, "Date of birth is required")
    .refine(
      (val) => {
        const dob = new Date(val);
        const today = new Date();
        const age = today.getFullYear() - dob.getFullYear();
        const monthDiff = today.getMonth() - dob.getMonth();
        const adjustedAge =
          monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())
            ? age - 1
            : age;
        return adjustedAge >= 18;
      },
      { message: "You must be at least 18 years old to register" },
    ),
  sex: z.enum(["Male", "Female", "Prefer not to say"], {
    message: "Please select your sex",
  }),
  civil_status: z.enum(["Single", "Married", "Widowed", "Separated"], {
    message: "Please select civil status",
  }),
  contact_number: z
    .string()
    .min(1, "Contact number is required")
    .regex(
      /^\+63\s?9\d{2}\s?\d{3}\s?\d{4}$/,
      "Please enter a valid Philippine mobile number (+63 9XX XXX XXXX)",
    ),
  alt_contact_number: z
    .string()
    .regex(
      /^(\+63\s?9\d{2}\s?\d{3}\s?\d{4})?$/,
      "Invalid Philippine mobile number format",
    )
    .optional()
    .or(z.literal("")),
  alt_contact_name: z.string().optional().or(z.literal("")),
  alt_contact_relationship: z.string().optional().or(z.literal("")),
  is_pwd: z.boolean(),
  is_senior_citizen: z.boolean(),
  household_members: z.coerce
    .number({ message: "Required" })
    .int()
    .min(1, "Minimum 1 household member"),
  children_count: z.coerce.number().int().min(0).optional().or(z.nan()),
  senior_count: z.coerce.number().int().min(0).optional().or(z.nan()),
  pwd_count: z.coerce.number().int().min(0).optional().or(z.nan()),
});

const step3Schema = z.object({
  barangay: z.string().min(1, "Please select your barangay"),
  purok: z.string().optional().or(z.literal("")),
  street_address: z.string().min(1, "Street / house number is required"),
  nearest_landmark: z.string().optional().or(z.literal("")),
  home_type: z.enum(["Concrete", "Semi-Concrete", "Wood", "Makeshift"], {
    message: "Please select home type",
  }),
  floor_level: z.enum(["Ground Floor", "2nd Floor", "3rd Floor or higher"], {
    message: "Please select floor level",
  }),
  has_flood_experience: z.boolean(),
  most_recent_flood_year: z.coerce
    .number()
    .int()
    .min(1990)
    .max(new Date().getFullYear())
    .optional()
    .or(z.nan()),
  sms_alerts: z.boolean(),
  email_alerts: z.boolean(),
  push_notifications: z.boolean(),
  preferred_language: z.enum(["Filipino", "English"]),
});

type Step1Data = z.infer<typeof step1Schema>;
type Step2Data = z.infer<typeof step2Schema>;
type Step3Data = z.infer<typeof step3Schema>;

/* ================================================================== */
/*  Animation Variants                                                 */
/* ================================================================== */

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 30 : -30,
    opacity: 0,
  }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({
    x: direction > 0 ? -30 : 30,
    opacity: 0,
  }),
};

const containerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: "easeOut" as const },
  },
} as const;

const STEP_LABELS = ["Account", "Personal", "Address", "Review"];

/* ================================================================== */
/*  Styled Select Field                                                */
/* ================================================================== */

function SelectField({
  id,
  label,
  placeholder,
  options,
  value,
  onChange,
  error,
  disabled,
}: {
  id: string;
  label: string;
  placeholder: string;
  options: readonly string[];
  value: string;
  onChange: (v: string) => void;
  error?: string;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-sm font-medium text-foreground/90">
        {label}
      </Label>
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger
          id={id}
          className={cn(
            "h-11 rounded-xl border bg-background/50 backdrop-blur-sm",
            "focus:ring-2 focus:ring-primary/30 focus:border-primary/50",
            "hover:border-primary/30 hover:bg-background/70",
            error
              ? "border-destructive/50 focus:ring-destructive/30"
              : "border-border/50",
          )}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
        >
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt} value={opt}>
              {opt}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <AnimatePresence>
        {error && (
          <motion.p
            id={`${id}-error`}
            role="alert"
            className="text-xs font-medium text-destructive"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.2 }}
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ================================================================== */
/*  Step 1 — Account Information                                       */
/* ================================================================== */

function Step1Account({
  form,
  onNext,
  isSubmitting,
}: {
  form: UseFormReturn<Step1Data>;
  onNext: (data: Step1Data) => void;
  isSubmitting: boolean;
}) {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const passwordValue = useWatch({ control: form.control, name: "password" });

  return (
    <motion.form
      onSubmit={form.handleSubmit(onNext)}
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-4"
      noValidate
    >
      <motion.div variants={itemVariants}>
        <FormField
          id="reg-name"
          label="Full Name"
          icon={User}
          type="text"
          placeholder="Juan Dela Cruz"
          autoComplete="name"
          disabled={isSubmitting}
          error={form.formState.errors.full_name?.message}
          {...form.register("full_name")}
        />
      </motion.div>

      <motion.div variants={itemVariants}>
        <FormField
          id="reg-email"
          label="Email Address"
          icon={Mail}
          type="email"
          placeholder="name@example.com"
          autoComplete="email"
          disabled={isSubmitting}
          error={form.formState.errors.email?.message}
          {...form.register("email")}
        />
      </motion.div>

      <motion.div variants={itemVariants}>
        <FormField
          id="reg-password"
          label="Password"
          icon={Lock}
          type={showPassword ? "text" : "password"}
          placeholder="Create a strong password"
          autoComplete="new-password"
          disabled={isSubmitting}
          error={form.formState.errors.password?.message}
          {...form.register("password")}
          trailing={
            <button
              type="button"
              className="text-muted-foreground/60 hover:text-foreground transition-colors"
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
        <div className="mt-2">
          <PasswordStrengthMeter password={passwordValue || ""} />
        </div>
        <PasswordRequirements password={passwordValue || ""} />
      </motion.div>

      <motion.div variants={itemVariants}>
        <FormField
          id="reg-confirm-password"
          label="Confirm Password"
          icon={Lock}
          type={showConfirm ? "text" : "password"}
          placeholder="Confirm your password"
          autoComplete="new-password"
          disabled={isSubmitting}
          error={form.formState.errors.confirm_password?.message}
          {...form.register("confirm_password")}
          trailing={
            <button
              type="button"
              className="text-muted-foreground/60 hover:text-foreground transition-colors"
              onClick={() => setShowConfirm((v) => !v)}
              aria-label={showConfirm ? "Hide password" : "Show password"}
              tabIndex={-1}
            >
              {showConfirm ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          }
        />
      </motion.div>

      <motion.div variants={itemVariants}>
        <Button
          type="submit"
          className="w-full h-11 rounded-xl bg-linear-to-r from-primary to-primary/90 shadow-lg shadow-primary/20 transition-all duration-300"
          disabled={isSubmitting}
        >
          Next: Personal Information
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </motion.div>
    </motion.form>
  );
}

/* ================================================================== */
/*  Step 2 — Personal & Household Information                          */
/* ================================================================== */

function Step2Personal({
  form,
  onNext,
  onBack,
  isSubmitting,
}: {
  form: UseFormReturn<Step2Data>;
  onNext: (data: Step2Data) => void;
  onBack: () => void;
  isSubmitting: boolean;
}) {
  return (
    <motion.form
      onSubmit={form.handleSubmit(onNext)}
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-4"
      noValidate
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <motion.div variants={itemVariants}>
          <FormField
            id="reg-dob"
            label="Date of Birth"
            type="date"
            disabled={isSubmitting}
            error={form.formState.errors.date_of_birth?.message}
            {...form.register("date_of_birth")}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <Controller
            control={form.control}
            name="sex"
            render={({ field }) => (
              <SelectField
                id="reg-sex"
                label="Sex"
                placeholder="Select sex"
                options={SEX_OPTIONS}
                value={field.value ?? ""}
                onChange={field.onChange}
                error={form.formState.errors.sex?.message}
                disabled={isSubmitting}
              />
            )}
          />
        </motion.div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <motion.div variants={itemVariants}>
          <Controller
            control={form.control}
            name="civil_status"
            render={({ field }) => (
              <SelectField
                id="reg-civil-status"
                label="Civil Status"
                placeholder="Select status"
                options={CIVIL_STATUS_OPTIONS}
                value={field.value ?? ""}
                onChange={field.onChange}
                error={form.formState.errors.civil_status?.message}
                disabled={isSubmitting}
              />
            )}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <FormField
            id="reg-contact"
            label="Contact Number"
            icon={Phone}
            type="tel"
            placeholder="+63 9XX XXX XXXX"
            autoComplete="tel"
            disabled={isSubmitting}
            error={form.formState.errors.contact_number?.message}
            {...form.register("contact_number")}
          />
        </motion.div>
      </div>

      {/* Alternative contact */}
      <motion.div
        variants={itemVariants}
        className="rounded-xl border border-border/30 bg-muted/30 p-4 space-y-3"
      >
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Alternative Contact (Optional)
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormField
            id="reg-alt-name"
            label="Contact Person Name"
            type="text"
            placeholder="e.g., Maria Cruz"
            disabled={isSubmitting}
            {...form.register("alt_contact_name")}
          />
          <FormField
            id="reg-alt-phone"
            label="Phone Number"
            icon={Phone}
            type="tel"
            placeholder="+63 9XX XXX XXXX"
            disabled={isSubmitting}
            error={form.formState.errors.alt_contact_number?.message}
            {...form.register("alt_contact_number")}
          />
        </div>
        <FormField
          id="reg-alt-rel"
          label="Relationship"
          type="text"
          placeholder="e.g., Spouse, Parent, Sibling"
          disabled={isSubmitting}
          {...form.register("alt_contact_relationship")}
        />
      </motion.div>

      {/* PWD / Senior Citizen */}
      <motion.div variants={itemVariants} className="flex flex-wrap gap-6">
        <Controller
          control={form.control}
          name="is_pwd"
          render={({ field }) => (
            <div className="flex items-center gap-2">
              <Checkbox
                id="reg-pwd"
                checked={field.value}
                onCheckedChange={field.onChange}
                disabled={isSubmitting}
              />
              <Label htmlFor="reg-pwd" className="text-sm cursor-pointer">
                Person with Disability (PWD)
              </Label>
            </div>
          )}
        />
        <Controller
          control={form.control}
          name="is_senior_citizen"
          render={({ field }) => (
            <div className="flex items-center gap-2">
              <Checkbox
                id="reg-senior"
                checked={field.value}
                onCheckedChange={field.onChange}
                disabled={isSubmitting}
              />
              <Label htmlFor="reg-senior" className="text-sm cursor-pointer">
                Senior Citizen
              </Label>
            </div>
          )}
        />
      </motion.div>

      {/* Household counts */}
      <motion.div variants={itemVariants}>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
          <Users className="inline h-3.5 w-3.5 mr-1" />
          Household Composition
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <FormField
            id="reg-hh-members"
            label="Total Members"
            type="number"
            min={1}
            disabled={isSubmitting}
            error={form.formState.errors.household_members?.message}
            {...form.register("household_members")}
          />
          <FormField
            id="reg-children"
            label="Children (0-12)"
            type="number"
            min={0}
            disabled={isSubmitting}
            {...form.register("children_count")}
          />
          <FormField
            id="reg-seniors"
            label="Seniors"
            type="number"
            min={0}
            disabled={isSubmitting}
            {...form.register("senior_count")}
          />
          <FormField
            id="reg-pwds"
            label="PWDs"
            type="number"
            min={0}
            disabled={isSubmitting}
            {...form.register("pwd_count")}
          />
        </div>
      </motion.div>

      {/* Navigation */}
      <motion.div variants={itemVariants} className="flex gap-3">
        <Button
          type="button"
          variant="outline"
          className="flex-1 h-11 rounded-xl"
          onClick={onBack}
          disabled={isSubmitting}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Button
          type="submit"
          className="flex-1 h-11 rounded-xl bg-linear-to-r from-primary to-primary/90 shadow-lg shadow-primary/20"
          disabled={isSubmitting}
        >
          Next: Address
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </motion.div>
    </motion.form>
  );
}

/* ================================================================== */
/*  Step 3 — Address, Location & Notifications                         */
/* ================================================================== */

function Step3Address({
  form,
  onNext,
  onBack,
  isSubmitting,
}: {
  form: UseFormReturn<Step3Data>;
  onNext: (data: Step3Data) => void;
  onBack: () => void;
  isSubmitting: boolean;
}) {
  const selectedBarangay = useWatch({
    control: form.control,
    name: "barangay",
  });
  const hasFloodExp = useWatch({
    control: form.control,
    name: "has_flood_experience",
  });
  const barangayInfo = selectedBarangay
    ? getBarangayInfo(selectedBarangay)
    : null;

  return (
    <motion.form
      onSubmit={form.handleSubmit(onNext)}
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-4"
      noValidate
    >
      {/* Barangay + auto-populated info */}
      <motion.div variants={itemVariants}>
        <Controller
          control={form.control}
          name="barangay"
          render={({ field }) => (
            <SelectField
              id="reg-barangay"
              label="Barangay"
              placeholder="Select your barangay"
              options={BARANGAY_NAMES}
              value={field.value ?? ""}
              onChange={field.onChange}
              error={form.formState.errors.barangay?.message}
              disabled={isSubmitting}
            />
          )}
        />
        {barangayInfo && (
          <motion.div
            className="mt-2 flex flex-wrap gap-2"
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Badge variant="outline" className="text-xs">
              <MapPin className="h-3 w-3 mr-1" />
              {barangayInfo.zoneType}
            </Badge>
            <Badge
              variant="outline"
              className={cn(
                "text-xs",
                barangayInfo.floodRisk === "High" &&
                  "border-risk-critical/30 text-risk-critical bg-risk-critical/10",
                barangayInfo.floodRisk === "Moderate" &&
                  "border-risk-alert/30 text-risk-alert bg-risk-alert/10",
                barangayInfo.floodRisk === "Low" &&
                  "border-risk-safe/30 text-risk-safe bg-risk-safe/10",
              )}
            >
              Risk: {barangayInfo.floodRisk}
            </Badge>
            <Badge variant="outline" className="text-xs">
              <Shield className="h-3 w-3 mr-1" />
              {barangayInfo.evacuationCenter}
            </Badge>
          </motion.div>
        )}
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <motion.div variants={itemVariants}>
          <FormField
            id="reg-purok"
            label="Purok / Zone / Sitio"
            type="text"
            placeholder="Optional"
            disabled={isSubmitting}
            {...form.register("purok")}
          />
        </motion.div>
        <motion.div variants={itemVariants}>
          <FormField
            id="reg-street"
            label="Street / House Number"
            icon={Home}
            type="text"
            placeholder="123 Rizal St."
            disabled={isSubmitting}
            error={form.formState.errors.street_address?.message}
            {...form.register("street_address")}
          />
        </motion.div>
      </div>

      <motion.div variants={itemVariants}>
        <FormField
          id="reg-landmark"
          label="Nearest Landmark"
          type="text"
          placeholder="Optional — helps responders locate your household"
          disabled={isSubmitting}
          {...form.register("nearest_landmark")}
        />
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <motion.div variants={itemVariants}>
          <Controller
            control={form.control}
            name="home_type"
            render={({ field }) => (
              <SelectField
                id="reg-home-type"
                label="Home Type"
                placeholder="Select type"
                options={HOME_TYPE_OPTIONS}
                value={field.value ?? ""}
                onChange={field.onChange}
                error={form.formState.errors.home_type?.message}
                disabled={isSubmitting}
              />
            )}
          />
        </motion.div>
        <motion.div variants={itemVariants}>
          <Controller
            control={form.control}
            name="floor_level"
            render={({ field }) => (
              <SelectField
                id="reg-floor"
                label="Floor Level"
                placeholder="Select level"
                options={FLOOR_LEVEL_OPTIONS}
                value={field.value ?? ""}
                onChange={field.onChange}
                error={form.formState.errors.floor_level?.message}
                disabled={isSubmitting}
              />
            )}
          />
        </motion.div>
      </div>

      {/* Flood experience */}
      <motion.div variants={itemVariants} className="space-y-3">
        <Controller
          control={form.control}
          name="has_flood_experience"
          render={({ field }) => (
            <div className="flex items-center gap-2">
              <Checkbox
                id="reg-flood-exp"
                checked={field.value}
                onCheckedChange={field.onChange}
                disabled={isSubmitting}
              />
              <Label htmlFor="reg-flood-exp" className="text-sm cursor-pointer">
                My household has experienced flooding before
              </Label>
            </div>
          )}
        />
        {hasFloodExp && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <FormField
              id="reg-flood-year"
              label="Most Recent Flood Year"
              type="number"
              min={1990}
              max={new Date().getFullYear()}
              placeholder={String(new Date().getFullYear())}
              disabled={isSubmitting}
              {...form.register("most_recent_flood_year")}
            />
          </motion.div>
        )}
      </motion.div>

      {/* Notification Preferences */}
      <motion.div
        variants={itemVariants}
        className="rounded-xl border border-border/30 bg-muted/30 p-4 space-y-3"
      >
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Notification Preferences
        </p>
        <div className="space-y-3">
          <Controller
            control={form.control}
            name="sms_alerts"
            render={({ field }) => (
              <div className="flex items-center justify-between">
                <Label htmlFor="reg-sms" className="text-sm">
                  SMS Flood Alerts
                </Label>
                <Switch
                  id="reg-sms"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  disabled={isSubmitting}
                />
              </div>
            )}
          />
          <Controller
            control={form.control}
            name="email_alerts"
            render={({ field }) => (
              <div className="flex items-center justify-between">
                <Label htmlFor="reg-email-alert" className="text-sm">
                  Email Flood Alerts
                </Label>
                <Switch
                  id="reg-email-alert"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  disabled={isSubmitting}
                />
              </div>
            )}
          />
          <Controller
            control={form.control}
            name="push_notifications"
            render={({ field }) => (
              <div className="flex items-center justify-between">
                <Label htmlFor="reg-push" className="text-sm">
                  Push Notifications
                </Label>
                <Switch
                  id="reg-push"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  disabled={isSubmitting}
                />
              </div>
            )}
          />
          <Controller
            control={form.control}
            name="preferred_language"
            render={({ field }) => (
              <SelectField
                id="reg-lang"
                label="Preferred Alert Language"
                placeholder="Select language"
                options={ALERT_LANGUAGE_OPTIONS}
                value={field.value}
                onChange={field.onChange}
                disabled={isSubmitting}
              />
            )}
          />
        </div>
      </motion.div>

      {/* Navigation */}
      <motion.div variants={itemVariants} className="flex gap-3">
        <Button
          type="button"
          variant="outline"
          className="flex-1 h-11 rounded-xl"
          onClick={onBack}
          disabled={isSubmitting}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Button
          type="submit"
          className="flex-1 h-11 rounded-xl bg-linear-to-r from-primary to-primary/90 shadow-lg shadow-primary/20"
          disabled={isSubmitting}
        >
          Review & Submit
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </motion.div>
    </motion.form>
  );
}

/* ================================================================== */
/*  Step 4 — Review & Submit                                           */
/* ================================================================== */

function ReviewSection({
  title,
  icon: Icon,
  onEdit,
  children,
}: {
  title: string;
  icon: React.ElementType;
  onEdit: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border/30 bg-muted/20 p-4 space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold flex items-center gap-1.5">
          <Icon className="h-4 w-4 text-primary" />
          {title}
        </h4>
        <button
          type="button"
          onClick={onEdit}
          className="text-xs text-primary hover:underline inline-flex items-center gap-1"
        >
          <Pencil className="h-3 w-3" />
          Edit
        </button>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">{children}</div>
    </div>
  );
}

function ReviewField({
  label,
  value,
}: {
  label: string;
  value: string | number | boolean | undefined | null;
}) {
  const display =
    value === true
      ? "Yes"
      : value === false
        ? "No"
        : value === undefined ||
            value === null ||
            value === "" ||
            Number.isNaN(value)
          ? "—"
          : String(value);

  return (
    <div className="py-0.5">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="font-medium truncate">{display}</p>
    </div>
  );
}

function Step4Review({
  step1Data,
  step2Data,
  step3Data,
  onBack,
  onEdit,
  onSubmit,
  isSubmitting,
  error,
}: {
  step1Data: Step1Data;
  step2Data: Step2Data;
  step3Data: Step3Data;
  onBack: () => void;
  onEdit: (step: number) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  error: string | null;
}) {
  const [consentChecked, setConsentChecked] = useState(false);
  const barangayInfo = getBarangayInfo(step3Data.barangay);

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-4"
    >
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <Alert
              variant="destructive"
              role="alert"
              className="border-destructive/30 bg-destructive/10"
            >
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div variants={itemVariants}>
        <ReviewSection title="Account" icon={User} onEdit={() => onEdit(1)}>
          <ReviewField label="Full Name" value={step1Data.full_name} />
          <ReviewField label="Email" value={step1Data.email} />
        </ReviewSection>
      </motion.div>

      <motion.div variants={itemVariants}>
        <ReviewSection title="Personal" icon={Users} onEdit={() => onEdit(2)}>
          <ReviewField label="Date of Birth" value={step2Data.date_of_birth} />
          <ReviewField label="Sex" value={step2Data.sex} />
          <ReviewField label="Civil Status" value={step2Data.civil_status} />
          <ReviewField label="Contact" value={step2Data.contact_number} />
          <ReviewField
            label="Alt. Contact"
            value={
              step2Data.alt_contact_name
                ? `${step2Data.alt_contact_name} (${step2Data.alt_contact_relationship || "—"})`
                : undefined
            }
          />
          <ReviewField
            label="Alt. Phone"
            value={step2Data.alt_contact_number}
          />
          <ReviewField
            label="Household Members"
            value={step2Data.household_members}
          />
          <ReviewField
            label="Children (0-12)"
            value={step2Data.children_count}
          />
          <ReviewField label="Senior Citizens" value={step2Data.senior_count} />
          <ReviewField label="PWDs" value={step2Data.pwd_count} />
          <ReviewField label="Is PWD" value={step2Data.is_pwd} />
          <ReviewField
            label="Senior Citizen"
            value={step2Data.is_senior_citizen}
          />
        </ReviewSection>
      </motion.div>

      <motion.div variants={itemVariants}>
        <ReviewSection title="Address" icon={MapPin} onEdit={() => onEdit(3)}>
          <ReviewField label="Barangay" value={step3Data.barangay} />
          <ReviewField label="Zone Type" value={barangayInfo?.zoneType} />
          <ReviewField label="Flood Risk" value={barangayInfo?.floodRisk} />
          <ReviewField
            label="Evacuation Center"
            value={barangayInfo?.evacuationCenter}
          />
          <ReviewField label="Purok / Zone" value={step3Data.purok} />
          <ReviewField label="Street" value={step3Data.street_address} />
          <ReviewField
            label="Nearest Landmark"
            value={step3Data.nearest_landmark}
          />
          <ReviewField label="Home Type" value={step3Data.home_type} />
          <ReviewField label="Floor Level" value={step3Data.floor_level} />
          <ReviewField
            label="Flood Experience"
            value={step3Data.has_flood_experience}
          />
          {step3Data.has_flood_experience && (
            <ReviewField
              label="Last Flood Year"
              value={step3Data.most_recent_flood_year}
            />
          )}
          <ReviewField
            label="Notifications"
            value={
              [
                step3Data.sms_alerts && "SMS",
                step3Data.email_alerts && "Email",
                step3Data.push_notifications && "Push",
              ]
                .filter(Boolean)
                .join(", ") || "None"
            }
          />
          <ReviewField
            label="Alert Language"
            value={step3Data.preferred_language}
          />
        </ReviewSection>
      </motion.div>

      {/* Consent */}
      <motion.div
        variants={itemVariants}
        className="rounded-xl border border-border/30 bg-muted/20 p-4 space-y-3"
      >
        <div className="flex items-start gap-2">
          <Checkbox
            id="reg-consent"
            checked={consentChecked}
            onCheckedChange={(checked) => setConsentChecked(checked === true)}
            className="mt-0.5"
          />
          <Label
            htmlFor="reg-consent"
            className="text-xs text-muted-foreground leading-relaxed cursor-pointer"
          >
            I consent to the collection and use of my personal information for
            flood emergency management purposes in accordance with the
            Philippine Data Privacy Act (RA 10173).
          </Label>
        </div>
        <p className="text-[11px] text-muted-foreground/60 pl-6">
          Your data will be used exclusively for DRRM emergency response and
          will not be shared with third parties.
        </p>
      </motion.div>

      {/* Navigation */}
      <motion.div variants={itemVariants} className="flex gap-3">
        <Button
          type="button"
          variant="outline"
          className="flex-1 h-11 rounded-xl"
          onClick={onBack}
          disabled={isSubmitting}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Button
          type="button"
          className="flex-1 h-11 rounded-xl bg-linear-to-r from-primary to-primary/90 shadow-lg shadow-primary/20"
          disabled={isSubmitting || !consentChecked}
          onClick={onSubmit}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Registering...
            </>
          ) : (
            <>
              <UserPlus className="mr-2 h-4 w-4" />
              Complete Registration
            </>
          )}
        </Button>
      </motion.div>
    </motion.div>
  );
}

/* ================================================================== */
/*  Success Screen                                                     */
/* ================================================================== */

function RegistrationSuccess() {
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
          <h2 className="text-2xl font-bold">Registration Successful!</h2>
          <p className="text-sm text-muted-foreground max-w-sm">
            Your account is pending verification. Please check your email for a
            verification link.
          </p>
        </div>
        <div className="rounded-xl border border-border/30 bg-muted/20 p-4 text-left text-sm space-y-2 w-full max-w-sm">
          <p className="font-medium text-foreground/90">What happens next?</p>
          <ol className="list-decimal list-inside text-muted-foreground space-y-1 text-xs">
            <li>
              Check your email inbox (and spam folder) for the verification link
            </li>
            <li>Click the link to verify your email address</li>
            <li>An LGU operator will verify your barangay assignment</li>
            <li>
              You&apos;ll receive a confirmation once your account is active
            </li>
          </ol>
        </div>
        <Link to="/login" className="w-full max-w-sm">
          <Button className="w-full h-11 rounded-xl bg-linear-to-r from-primary to-primary/90 shadow-lg shadow-primary/20">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Sign In
          </Button>
        </Link>
      </motion.div>
    </GlassCard>
  );
}

/* ================================================================== */
/*  Error Helpers                                                      */
/* ================================================================== */

/** Parse API error into a user-friendly registration error message */
function getRegistrationErrorMessage(error: unknown): string {
  const msg = (error as { message?: string })?.message ?? "";
  const code = (error as { code?: string })?.code ?? "";
  const lower = msg.toLowerCase();

  if (
    code === "EMAIL_EXISTS" ||
    lower.includes("already exists") ||
    lower.includes("already registered")
  ) {
    return "An account with this email already exists. Sign in or reset your password.";
  }
  if (code === "UNDERAGE" || lower.includes("18")) {
    return "You must be at least 18 years old to register.";
  }
  if (code === "RATE_LIMITED" || lower.includes("too many")) {
    return "Too many registration attempts. Please try again later.";
  }
  if (lower.includes("phone") || lower.includes("contact")) {
    return "Please enter a valid Philippine mobile number (+63 9XX XXX XXXX).";
  }
  return msg || "Registration failed. Please try again.";
}

/* ================================================================== */
/*  Main Wizard Component                                              */
/* ================================================================== */

export function RegistrationWizard() {
  const { registerResident, isRegisteringResident, registerResidentError } =
    useAuth();

  const [currentStep, setCurrentStep] = useState(1);
  const [direction, setDirection] = useState(1);
  const [isComplete, setIsComplete] = useState(false);

  // Persisted step data
  const [step1Data, setStep1Data] = useState<Step1Data | null>(null);
  const [step2Data, setStep2Data] = useState<Step2Data | null>(null);
  const [step3Data, setStep3Data] = useState<Step3Data | null>(null);

  // Forms
  const step1Form = useForm<Step1Data>({
    resolver: zodResolver(step1Schema),
    defaultValues: {
      full_name: step1Data?.full_name ?? "",
      email: step1Data?.email ?? "",
      password: step1Data?.password ?? "",
      confirm_password: step1Data?.confirm_password ?? "",
    },
    mode: "onBlur",
  });

  const step2Form = useForm<Step2Data>({
    resolver: zodResolver(step2Schema) as Resolver<Step2Data>,
    defaultValues: {
      date_of_birth: step2Data?.date_of_birth ?? "",
      sex: step2Data?.sex,
      civil_status: step2Data?.civil_status,
      contact_number: step2Data?.contact_number ?? "",
      alt_contact_number: step2Data?.alt_contact_number ?? "",
      alt_contact_name: step2Data?.alt_contact_name ?? "",
      alt_contact_relationship: step2Data?.alt_contact_relationship ?? "",
      is_pwd: step2Data?.is_pwd ?? false,
      is_senior_citizen: step2Data?.is_senior_citizen ?? false,
      household_members: step2Data?.household_members ?? 1,
      children_count: step2Data?.children_count,
      senior_count: step2Data?.senior_count,
      pwd_count: step2Data?.pwd_count,
    },
    mode: "onBlur",
  });

  const step3Form = useForm<Step3Data>({
    resolver: zodResolver(step3Schema) as Resolver<Step3Data>,
    defaultValues: {
      barangay: step3Data?.barangay ?? "",
      purok: step3Data?.purok ?? "",
      street_address: step3Data?.street_address ?? "",
      nearest_landmark: step3Data?.nearest_landmark ?? "",
      home_type: step3Data?.home_type,
      floor_level: step3Data?.floor_level,
      has_flood_experience: step3Data?.has_flood_experience ?? false,
      most_recent_flood_year: step3Data?.most_recent_flood_year,
      sms_alerts: step3Data?.sms_alerts ?? true,
      email_alerts: step3Data?.email_alerts ?? true,
      push_notifications: step3Data?.push_notifications ?? true,
      preferred_language: step3Data?.preferred_language ?? "Filipino",
    },
    mode: "onBlur",
  });

  const goTo = useCallback(
    (step: number) => {
      setDirection(step > currentStep ? 1 : -1);
      setCurrentStep(step);
    },
    [currentStep],
  );

  const handleStep1Next = useCallback((data: Step1Data) => {
    setStep1Data(data);
    setDirection(1);
    setCurrentStep(2);
  }, []);

  const handleStep2Next = useCallback((data: Step2Data) => {
    setStep2Data(data);
    setDirection(1);
    setCurrentStep(3);
  }, []);

  const handleStep3Next = useCallback((data: Step3Data) => {
    setStep3Data(data);
    setDirection(1);
    setCurrentStep(4);
  }, []);

  const handleBack = useCallback(() => {
    setDirection(-1);
    setCurrentStep((s) => Math.max(1, s - 1));
  }, []);

  const handleFinalSubmit = useCallback(() => {
    if (!step1Data || !step2Data || !step3Data) return;

    registerResident(
      {
        // Step 1 — Account
        full_name: step1Data.full_name,
        email: step1Data.email,
        password: step1Data.password,

        // Step 2 — Personal & Household
        date_of_birth: step2Data.date_of_birth,
        sex: step2Data.sex,
        civil_status: step2Data.civil_status,
        contact_number: step2Data.contact_number,
        alt_contact_number: step2Data.alt_contact_number || undefined,
        alt_contact_name: step2Data.alt_contact_name || undefined,
        alt_contact_relationship:
          step2Data.alt_contact_relationship || undefined,
        is_pwd: step2Data.is_pwd,
        is_senior_citizen: step2Data.is_senior_citizen,
        household_members: step2Data.household_members,
        children_count: Number.isNaN(step2Data.children_count)
          ? undefined
          : step2Data.children_count,
        senior_count: Number.isNaN(step2Data.senior_count)
          ? undefined
          : step2Data.senior_count,
        pwd_count: Number.isNaN(step2Data.pwd_count)
          ? undefined
          : step2Data.pwd_count,

        // Step 3 — Address & Location
        barangay: step3Data.barangay,
        purok: step3Data.purok || undefined,
        street_address: step3Data.street_address,
        nearest_landmark: step3Data.nearest_landmark || undefined,
        home_type: step3Data.home_type,
        floor_level: step3Data.floor_level,
        has_flood_experience: step3Data.has_flood_experience,
        most_recent_flood_year: Number.isNaN(step3Data.most_recent_flood_year)
          ? undefined
          : step3Data.most_recent_flood_year,

        // Notifications
        sms_alerts: step3Data.sms_alerts,
        email_alerts: step3Data.email_alerts,
        push_notifications: step3Data.push_notifications,
        preferred_language: step3Data.preferred_language,

        // Consent
        data_privacy_consent: true,
      },
      {
        onSuccess: () => {
          setIsComplete(true);
        },
      },
    );
  }, [step1Data, step2Data, step3Data, registerResident]);

  const registrationError = registerResidentError
    ? getRegistrationErrorMessage(registerResidentError)
    : null;

  if (isComplete) {
    return <RegistrationSuccess />;
  }

  return (
    <GlassCard intensity="medium" className="w-full overflow-hidden">
      <div className="h-1 w-full bg-linear-to-r from-primary/80 via-primary to-primary/80" />

      <div className="p-6 space-y-4">
        {/* Mobile-only status */}
        <div className="flex justify-center lg:hidden">
          <CityStatusBadge />
        </div>

        {/* Header */}
        <div className="space-y-1.5 text-center">
          <h2 className="text-xl font-bold tracking-tight">
            Create Your Account
          </h2>
          <p className="text-sm text-muted-foreground">
            Step {currentStep} of 4 &mdash; {STEP_LABELS[currentStep - 1]}
          </p>
        </div>

        {/* Progress */}
        <StepIndicator steps={4} current={currentStep} labels={STEP_LABELS} />

        {/* Step content */}
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={currentStep}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.25, ease: "easeInOut" }}
          >
            {currentStep === 1 && (
              <Step1Account
                form={step1Form}
                onNext={handleStep1Next}
                isSubmitting={isRegisteringResident}
              />
            )}
            {currentStep === 2 && (
              <Step2Personal
                form={step2Form}
                onNext={handleStep2Next}
                onBack={handleBack}
                isSubmitting={isRegisteringResident}
              />
            )}
            {currentStep === 3 && (
              <Step3Address
                form={step3Form}
                onNext={handleStep3Next}
                onBack={handleBack}
                isSubmitting={isRegisteringResident}
              />
            )}
            {currentStep === 4 && step1Data && step2Data && step3Data && (
              <Step4Review
                step1Data={step1Data}
                step2Data={step2Data}
                step3Data={step3Data}
                onBack={handleBack}
                onEdit={goTo}
                onSubmit={handleFinalSubmit}
                isSubmitting={isRegisteringResident}
                error={registrationError}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Footer */}
      <div className="px-6 pb-6 flex flex-col items-center space-y-2">
        <div className="w-full h-px bg-linear-to-r from-transparent via-border/50 to-transparent" />
        <p className="text-sm text-muted-foreground pt-2">
          Already have an account?{" "}
          <Link
            to="/login"
            className="text-primary font-medium underline-offset-4 hover:underline transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </GlassCard>
  );
}

export default RegistrationWizard;
