/**
 * Settings Page - Web 3.0 Edition
 *
 * User settings page with glassmorphism cards, enhanced form inputs,
 * password strength meter, gradient accents, and polished micro-interactions.
 */

import { zodResolver } from "@hookform/resolvers/zod";
import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  Bell,
  Check,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  LogOut,
  Mail,
  MessageSquare,
  Palette,
  Shield,
  User,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { SectionHeading } from "@/components/layout/SectionHeading";
import { fadeUp, staggerContainer } from "@/lib/motion";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordStrengthMeter } from "@/components/ui/password-strength-meter";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { BARANGAYS } from "@/config/paranaque";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import {
  useNotifications,
  useTheme,
  useUIActions,
  type NotificationPreferences,
} from "@/state";

const ROLE_LABELS: Record<string, string> = {
  admin: "Administrator",
  operator: "LGU Operator",
  user: "Resident",
};

const NOTIFICATION_LABELS: Record<string, string> = {
  emailAlerts: "Email Alerts",
  pushNotifications: "Push Notifications",
  weeklyDigest: "Weekly Digest",
};

/** Item entrance animation */
const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: "easeOut" as const },
  },
} as const;

/**
 * Profile form validation schema
 */
const profileSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Invalid email address"),
});

type ProfileFormValues = z.infer<typeof profileSchema>;

/**
 * Password change validation schema
 */
const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, "Current password is required"),
    newPassword: z
      .string()
      .min(12, "Password must be at least 12 characters")
      .regex(/[A-Z]/, "Must contain at least one uppercase letter")
      .regex(/[a-z]/, "Must contain at least one lowercase letter")
      .regex(/[0-9]/, "Must contain at least one digit")
      .regex(
        /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/,
        "Must contain at least one special character",
      ),
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type PasswordFormValues = z.infer<typeof passwordSchema>;

/**
 * SettingsPage - Web 3.0 User settings and preferences
 */
export default function SettingsPage() {
  const theme = useTheme();
  const { toggleTheme } = useUIActions();
  const notifications = useNotifications();
  const { toggleNotification } = useUIActions();
  const {
    subscribe: pushSubscribe,
    unsubscribe: pushUnsubscribe,
    isSubscribed: isPushSubscribed,
    isSubscribing: isPushSubscribing,
    isSupported: isPushSupported,
  } = usePushNotifications();
  const {
    user,
    updateProfile,
    isUpdatingProfile,
    changePassword,
    isChangingPassword,
    logout,
    isLoggingOut,
  } = useAuth();

  // Password visibility toggles
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // SMS Evacuation Alerts state
  const [smsEnabled, setSmsEnabled] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [smsBarangay, setSmsBarangay] = useState("");

  // Profile form
  const profileForm = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: user?.name || "",
      email: user?.email || "",
    },
  });

  // Password form
  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  const newPasswordValue = useWatch({
    control: passwordForm.control,
    name: "newPassword",
  });

  // Reset profile form when user data loads/changes
  useEffect(() => {
    if (user) {
      profileForm.reset({
        name: user.name || "",
        email: user.email || "",
      });
    }
  }, [user, profileForm]);

  // Validate Philippine phone number (+63 9XX XXX XXXX)
  const validatePhone = useCallback((value: string): string | null => {
    if (!value) return "Phone number is required when SMS alerts are enabled";
    const cleaned = value.replace(/[\s-]/g, "");
    if (!/^\+639\d{9}$/.test(cleaned)) {
      return "Enter a valid Philippine mobile number (+63 9XX XXX XXXX)";
    }
    return null;
  }, []);

  // Handle SMS toggle
  const handleSmsToggle = useCallback((enabled: boolean) => {
    setSmsEnabled(enabled);
    if (!enabled) {
      setPhoneError(null);
    }
    toast.success("Preference Updated", {
      description: `SMS Evacuation Alerts ${enabled ? "enabled" : "disabled"}.`,
    });
  }, []);

  // Handle phone number change
  const handlePhoneChange = useCallback(
    (value: string) => {
      setPhoneNumber(value);
      if (smsEnabled) {
        setPhoneError(validatePhone(value));
      }
    },
    [smsEnabled, validatePhone],
  );

  // Handle Send Test SMS
  const handleSendTestSms = useCallback(() => {
    const error = validatePhone(phoneNumber);
    if (error) {
      setPhoneError(error);
      return;
    }
    if (!smsBarangay) {
      toast.error("Barangay Required", {
        description: "Please select your barangay before sending a test SMS.",
      });
      return;
    }
    toast.success("Test SMS Sent", {
      description: `A test alert was sent to ${phoneNumber} for ${smsBarangay}.`,
    });
  }, [phoneNumber, smsBarangay, validatePhone]);

  // Handle profile update
  const handleProfileSubmit = useCallback(
    (data: ProfileFormValues) => {
      updateProfile(data, {
        onSuccess: () => {
          toast.success("Profile Updated", {
            description: "Your profile has been updated successfully.",
          });
        },
        onError: (error: Error) => {
          toast.error("Update Failed", {
            description: error.message || "Failed to update profile.",
          });
        },
      });
    },
    [updateProfile],
  );

  // Handle password change
  const handlePasswordSubmit = useCallback(
    (data: PasswordFormValues) => {
      changePassword(
        {
          current_password: data.currentPassword,
          new_password: data.newPassword,
        },
        {
          onSuccess: () => {
            toast.success("Password Changed", {
              description: "Your password has been changed successfully.",
            });
            passwordForm.reset();
          },
          onError: (error: Error) => {
            toast.error("Password Change Failed", {
              description: error.message || "Failed to change password.",
            });
          },
        },
      );
    },
    [changePassword, passwordForm],
  );

  // Handle logout
  const handleLogout = useCallback(() => {
    logout();
  }, [logout]);

  // Toggle notification preference
  const handleToggleNotification = useCallback(
    async (key: keyof NotificationPreferences) => {
      if (key === "pushNotifications" && isPushSupported) {
        const newValue = !notifications[key];
        if (newValue) {
          const ok = await pushSubscribe();
          if (!ok) {
            toast.error("Push Notifications", {
              description: "Permission denied or subscription failed.",
            });
            return;
          }
        } else {
          await pushUnsubscribe();
        }
      }
      toggleNotification(key);
      const newValue = !notifications[key];
      const label = NOTIFICATION_LABELS[key] ?? key;
      toast.success("Preference Updated", {
        description: `${label} has been ${newValue ? "enabled" : "disabled"}.`,
      });
    },
    [
      toggleNotification,
      notifications,
      isPushSupported,
      pushSubscribe,
      pushUnsubscribe,
    ],
  );

  const profileRef = useRef<HTMLDivElement>(null);
  const profileInView = useInView(profileRef, { once: true, amount: 0.1 });
  const prefsRef = useRef<HTMLDivElement>(null);
  const prefsInView = useInView(prefsRef, { once: true, amount: 0.1 });

  return (
    <div className="min-h-screen bg-background">
      {/* Profile & Password Section */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={profileRef}>
          <SectionHeading
            label="Account"
            title="Profile & Security"
            subtitle="Update your personal information and change your password."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={profileInView ? "show" : undefined}
            className="space-y-6"
          >
            {/* Profile Card */}
            <motion.div variants={fadeUp}>
              <GlassCard
                intensity="medium"
                className="overflow-hidden hover:shadow-lg transition-all duration-300"
              >
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <div className="p-6 pb-3 space-y-1">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                    Profile
                  </h3>
                  <p className="text-sm text-muted-foreground pl-10">
                    Update your personal information and email address
                  </p>
                </div>
                <form onSubmit={profileForm.handleSubmit(handleProfileSubmit)}>
                  <div className="px-6 pb-4 space-y-4">
                    <motion.div
                      variants={itemVariants}
                      initial="hidden"
                      animate={profileInView ? "show" : undefined}
                      className="grid gap-4 sm:grid-cols-2"
                    >
                      <FormField
                        id="name"
                        label="Full Name"
                        icon={User}
                        placeholder="Your name"
                        error={profileForm.formState.errors.name?.message}
                        {...profileForm.register("name")}
                      />
                      <FormField
                        id="email"
                        label="Email Address"
                        icon={Mail}
                        type="email"
                        placeholder="your@email.com"
                        error={profileForm.formState.errors.email?.message}
                        {...profileForm.register("email")}
                      />
                    </motion.div>
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-foreground/90">
                        Role
                      </Label>
                      <div className="inline-flex items-center gap-2 rounded-xl border border-border/50 bg-muted/30 px-3.5 py-2">
                        <Shield className="h-4 w-4 text-primary" />
                        <span className="text-sm font-medium">
                          {ROLE_LABELS[user?.role ?? ""] ??
                            user?.role ??
                            "User"}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="px-6 pb-6 flex items-center">
                    <Button
                      type="submit"
                      disabled={isUpdatingProfile}
                      className="rounded-xl bg-linear-to-r from-primary to-primary/90 shadow-lg shadow-primary/20 transition-all duration-300"
                    >
                      {isUpdatingProfile ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Check className="mr-2 h-4 w-4" />
                          Save Changes
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </GlassCard>
            </motion.div>

            {/* Password Card */}
            <motion.div variants={fadeUp}>
              <GlassCard
                intensity="medium"
                className="overflow-hidden hover:shadow-lg transition-all duration-300"
              >
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <div className="p-6 pb-3 space-y-1">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                      <Lock className="h-4 w-4 text-primary" />
                    </div>
                    Password
                  </h3>
                  <p className="text-sm text-muted-foreground pl-10">
                    Change your password to keep your account secure
                  </p>
                </div>
                <form
                  onSubmit={passwordForm.handleSubmit(handlePasswordSubmit)}
                >
                  <div className="px-6 pb-4 space-y-4">
                    <FormField
                      id="currentPassword"
                      label="Current Password"
                      icon={Lock}
                      type={showCurrentPassword ? "text" : "password"}
                      error={
                        passwordForm.formState.errors.currentPassword?.message
                      }
                      {...passwordForm.register("currentPassword")}
                      trailing={
                        <button
                          type="button"
                          className="text-muted-foreground/60 hover:text-foreground transition-colors duration-200"
                          onClick={() => setShowCurrentPassword((v) => !v)}
                          aria-label={
                            showCurrentPassword
                              ? "Hide password"
                              : "Show password"
                          }
                          tabIndex={-1}
                        >
                          {showCurrentPassword ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
                      }
                    />
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <FormField
                          id="newPassword"
                          label="New Password"
                          icon={Lock}
                          type={showNewPassword ? "text" : "password"}
                          error={
                            passwordForm.formState.errors.newPassword?.message
                          }
                          {...passwordForm.register("newPassword")}
                          trailing={
                            <button
                              type="button"
                              className="text-muted-foreground/60 hover:text-foreground transition-colors duration-200"
                              onClick={() => setShowNewPassword((v) => !v)}
                              aria-label={
                                showNewPassword
                                  ? "Hide password"
                                  : "Show password"
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
                          <PasswordStrengthMeter
                            password={newPasswordValue || ""}
                          />
                        </div>
                      </div>
                      <FormField
                        id="confirmPassword"
                        label="Confirm Password"
                        icon={Lock}
                        type={showConfirmPassword ? "text" : "password"}
                        error={
                          passwordForm.formState.errors.confirmPassword?.message
                        }
                        {...passwordForm.register("confirmPassword")}
                        trailing={
                          <button
                            type="button"
                            className="text-muted-foreground/60 hover:text-foreground transition-colors duration-200"
                            onClick={() => setShowConfirmPassword((v) => !v)}
                            aria-label={
                              showConfirmPassword
                                ? "Hide password"
                                : "Show password"
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
                    </div>
                  </div>
                  <div className="px-6 pb-6 flex items-center">
                    <Button
                      type="submit"
                      disabled={isChangingPassword}
                      className="rounded-xl bg-linear-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary text-white shadow-lg shadow-primary/20 transition-all duration-300"
                    >
                      {isChangingPassword ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Changing...
                        </>
                      ) : (
                        <>
                          <Lock className="mr-2 h-4 w-4" />
                          Change Password
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Preferences & Session Section */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={prefsRef}>
          <SectionHeading
            label="Preferences"
            title="Customization & Session"
            subtitle="Adjust theme, notification settings, and manage your active session."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={prefsInView ? "show" : undefined}
            className="space-y-6"
          >
            {/* Preferences Card */}
            <motion.div variants={fadeUp}>
              <GlassCard
                intensity="medium"
                className="overflow-hidden hover:shadow-lg transition-all duration-300"
              >
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <div className="p-6 pb-3 space-y-1">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                      <Palette className="h-4 w-4 text-primary" />
                    </div>
                    Preferences
                  </h3>
                  <p className="text-sm text-muted-foreground pl-10">
                    Customize your experience and notification settings
                  </p>
                </div>
                <div className="px-6 pb-6 space-y-6">
                  {/* Theme Toggle */}
                  <div className="flex items-center justify-between rounded-xl border border-border/50 bg-background/50 p-4 transition-all duration-200 hover:bg-background/70">
                    <div className="space-y-0.5">
                      <Label className="text-sm font-medium">Dark Mode</Label>
                      <p className="text-xs text-muted-foreground">
                        Switch between light and dark themes
                      </p>
                    </div>
                    <Switch
                      checked={theme === "dark"}
                      onCheckedChange={() => toggleTheme()}
                    />
                  </div>

                  <Separator className="bg-border/30" />

                  {/* Notification Settings */}
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <Bell className="h-4 w-4 text-muted-foreground" />
                      <Label className="text-sm font-medium">
                        Notifications
                      </Label>
                    </div>

                    <div className="space-y-3 pl-6">
                      {(
                        [
                          {
                            key: "emailAlerts" as const,
                            label: "Email Alerts",
                            desc: "Receive flood alerts via email",
                          },
                          {
                            key: "pushNotifications" as const,
                            label: "Push Notifications",
                            desc: "Receive real-time browser notifications",
                          },
                          {
                            key: "weeklyDigest" as const,
                            label: "Weekly Digest",
                            desc: "Receive weekly summary reports",
                          },
                        ] as const
                      ).map((notif) => (
                        <div
                          key={notif.key}
                          className="flex items-center justify-between rounded-xl border border-border/50 bg-background/50 p-3.5 transition-all duration-200 hover:bg-background/70"
                        >
                          <div className="space-y-0.5">
                            <Label className="text-sm font-normal">
                              {notif.label}
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              {notif.desc}
                            </p>
                          </div>
                          <Switch
                            checked={
                              notif.key === "pushNotifications"
                                ? isPushSubscribed
                                : notifications[notif.key]
                            }
                            disabled={
                              notif.key === "pushNotifications" &&
                              isPushSubscribing
                            }
                            onCheckedChange={() =>
                              handleToggleNotification(notif.key)
                            }
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  <Separator className="bg-border/30" />

                  {/* SMS Evacuation Alerts */}
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-4 w-4 text-muted-foreground" />
                      <Label className="text-sm font-medium">
                        SMS Evacuation Alerts
                      </Label>
                    </div>

                    <div className="space-y-3 pl-6">
                      <div className="rounded-xl border border-border/50 bg-background/50 p-3.5 space-y-3">
                        {import.meta.env.VITE_SMS_ENABLED !== "true" && (
                          <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/20 rounded-lg px-3 py-2">
                            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                            SMS gateway not configured. Your number will be
                            saved for when it goes live.
                          </div>
                        )}
                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label className="text-sm font-normal">
                              Enable SMS Alerts
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              Receive evacuation alerts via SMS
                            </p>
                          </div>
                          <Switch
                            checked={smsEnabled}
                            onCheckedChange={handleSmsToggle}
                          />
                        </div>

                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground">
                            Phone Number
                          </Label>
                          <Input
                            type="tel"
                            placeholder="+63 9XX XXX XXXX"
                            className={`h-8 text-sm ${phoneError ? "border-destructive" : ""}`}
                            value={phoneNumber}
                            onChange={(e) => handlePhoneChange(e.target.value)}
                            disabled={!smsEnabled}
                          />
                          {phoneError && (
                            <p className="text-xs text-destructive">
                              {phoneError}
                            </p>
                          )}
                        </div>

                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground">
                            Barangay
                          </Label>
                          <Select
                            value={smsBarangay}
                            onValueChange={setSmsBarangay}
                            disabled={!smsEnabled}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue placeholder="Select your barangay" />
                            </SelectTrigger>
                            <SelectContent>
                              {BARANGAYS.map((b) => (
                                <SelectItem key={b.key} value={b.name}>
                                  {b.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="w-full rounded-xl text-xs"
                          disabled={!smsEnabled || !phoneNumber || !smsBarangay}
                          onClick={handleSendTestSms}
                        >
                          <MessageSquare className="mr-2 h-3.5 w-3.5" />
                          Send Test SMS
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </GlassCard>
            </motion.div>

            {/* Session Card */}
            <motion.div variants={fadeUp}>
              <GlassCard
                intensity="light"
                className="overflow-hidden border-destructive/30"
              >
                <div className="h-1 w-full bg-linear-to-r from-destructive/60 via-destructive to-destructive/60" />
                <div className="p-6 pb-3 space-y-1">
                  <h3 className="text-lg font-semibold flex items-center gap-2 text-destructive">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-destructive/10">
                      <AlertTriangle className="h-4 w-4 text-destructive" />
                    </div>
                    Session
                  </h3>
                  <p className="text-sm text-muted-foreground pl-10">
                    Manage your active session
                  </p>
                </div>
                <div className="px-6 pb-6">
                  <div className="flex items-center justify-between rounded-xl border border-destructive/20 bg-destructive/5 p-4">
                    <div className="space-y-0.5">
                      <p className="font-medium">Sign Out</p>
                      <p className="text-sm text-muted-foreground">
                        Sign out of your account on this device
                      </p>
                    </div>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="destructive"
                          disabled={isLoggingOut}
                          className="rounded-xl shadow-lg shadow-destructive/20"
                        >
                          {isLoggingOut ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          ) : (
                            <LogOut className="mr-2 h-4 w-4" />
                          )}
                          Sign Out
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                          <AlertDialogDescription>
                            You will be signed out of your account and
                            redirected to the login page.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={handleLogout}>
                            Sign Out
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
