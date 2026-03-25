/**
 * Operator — Settings Page (Full Parity with Resident)
 *
 * Mirrors the resident settings layout with GlassCard sections,
 * PageHeader, SectionHeading, and FormField patterns.
 * Adds operator-specific fields: contact number, assigned area,
 * barangay coverage, and operator notification preferences.
 */

import {
  AlertTriangle,
  Bell,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  LogOut,
  Mail,
  MapPin,
  Palette,
  Radio,
  Settings,
  Shield,
  User,
} from "lucide-react";
import { useCallback, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { SectionHeading } from "@/components/layout/SectionHeading";
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
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { BARANGAYS } from "@/config/paranaque";
import { useAuth } from "@/features/auth";
import { showToast } from "@/lib/toast";
import { cn } from "@/lib/utils";
import {
  useNotifications,
  useTheme,
  useUIActions,
  useUser,
  type NotificationPreferences,
} from "@/state";

// ── Notification configs ─────────────────────────────────────────────────

const NOTIFICATION_ITEMS: {
  key: keyof NotificationPreferences;
  label: string;
  desc: string;
}[] = [
  {
    key: "emailAlerts",
    label: "Email Alerts",
    desc: "Receive flood risk notifications via email",
  },
  {
    key: "pushNotifications",
    label: "Push Notifications",
    desc: "Browser push notifications for critical alerts",
  },
  {
    key: "weeklyDigest",
    label: "Weekly Digest",
    desc: "Summary of flood events and predictions every Monday",
  },
];

const OPERATOR_NOTIFICATION_ITEMS = [
  {
    key: "criticalAlertsOnly" as const,
    label: "Critical Alerts Only",
    desc: "Only receive notifications for Critical risk level",
  },
  {
    key: "allBarangayAlerts" as const,
    label: "All Barangay Alerts",
    desc: "Receive alerts from all 16 barangays",
  },
  {
    key: "shiftHandoverReport" as const,
    label: "Shift Handover Report",
    desc: "Receive automated shift summary at end of duty",
  },
  {
    key: "dailyOperationsDigest" as const,
    label: "Daily Operations Digest",
    desc: "Morning briefing with overnight flood activity",
  },
];

type OperatorNotifKey = (typeof OPERATOR_NOTIFICATION_ITEMS)[number]["key"];

// ── Password strength helper (shared pattern with resident) ──────────────

function passwordStrength(pw: string): {
  label: string;
  color: string;
  pct: number;
} {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return { label: "Weak", color: "bg-red-500", pct: 20 };
  if (score <= 2) return { label: "Fair", color: "bg-amber-500", pct: 40 };
  if (score <= 3) return { label: "Good", color: "bg-yellow-500", pct: 60 };
  if (score <= 4) return { label: "Strong", color: "bg-green-500", pct: 80 };
  return { label: "Very Strong", color: "bg-emerald-500", pct: 100 };
}

export default function OperatorSettingsPage() {
  const user = useUser();
  const theme = useTheme();
  const { toggleTheme, toggleNotification } = useUIActions();
  const notifications = useNotifications();
  const {
    changePassword,
    isChangingPassword,
    updateProfile,
    isUpdatingProfile,
    logout,
    isLoggingOut,
  } = useAuth();

  // ── Profile form state ─────────────────────────────────────────
  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [contactNumber, setContactNumber] = useState("");
  const [assignedArea, setAssignedArea] = useState("");

  // ── Password form state ────────────────────────────────────────
  const [showPwForm, setShowPwForm] = useState(false);
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showCurrentPw, setShowCurrentPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);
  const [showConfirmPw, setShowConfirmPw] = useState(false);

  const strength = passwordStrength(newPw);
  const pwMatch = newPw === confirmPw;

  // ── Operator-specific state ────────────────────────────────────
  const [assignedBarangays, setAssignedBarangays] = useState<string[]>([]);
  const [operatorNotifPrefs, setOperatorNotifPrefs] = useState<
    Record<OperatorNotifKey, boolean>
  >({
    criticalAlertsOnly: false,
    allBarangayAlerts: true,
    shiftHandoverReport: true,
    dailyOperationsDigest: false,
  });

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((w) => w[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "?";

  // ── Handlers ───────────────────────────────────────────────────

  const handleProfileSubmit = useCallback(() => {
    updateProfile(
      { name, email },
      {
        onSuccess: () => {
          showToast.success("Profile updated successfully");
        },
        onError: (error: Error) => {
          showToast.error(error.message || "Failed to update profile");
        },
      },
    );
  }, [updateProfile, name, email]);

  const handlePasswordChange = useCallback(() => {
    changePassword(
      { current_password: currentPw, new_password: newPw },
      {
        onSuccess: () => {
          showToast.success("Password changed successfully");
          setShowPwForm(false);
          setCurrentPw("");
          setNewPw("");
          setConfirmPw("");
        },
        onError: (err: Error) => {
          showToast.error(err.message || "Failed to change password");
        },
      },
    );
  }, [changePassword, currentPw, newPw]);

  const handleToggleNotification = useCallback(
    (key: keyof NotificationPreferences) => {
      toggleNotification(key);
      const item = NOTIFICATION_ITEMS.find((n) => n.key === key);
      showToast.success(
        `${item?.label ?? key} ${!notifications[key] ? "enabled" : "disabled"}`,
      );
    },
    [toggleNotification, notifications],
  );

  const handleToggleOperatorNotif = useCallback(
    (key: OperatorNotifKey) => {
      setOperatorNotifPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
      const item = OPERATOR_NOTIFICATION_ITEMS.find((n) => n.key === key);
      showToast.success(
        `${item?.label ?? key} ${!operatorNotifPrefs[key] ? "enabled" : "disabled"}`,
      );
    },
    [operatorNotifPrefs],
  );

  const handleLogout = useCallback(() => {
    logout();
  }, [logout]);

  return (
    <div className="min-h-screen bg-background">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="container mx-auto max-w-4xl px-4 pt-6">
        <PageHeader
          icon={Settings}
          title="Settings"
          subtitle="Manage your operator account settings and preferences"
        />
      </div>

      {/* ── Profile & Password Section ───────────────────────────── */}
      <section className="py-10 bg-muted/30">
        <div className="container mx-auto max-w-4xl px-4">
          <SectionHeading
            label="Account"
            title="Profile & Security"
            subtitle="Update your personal information and change your password."
          />

          <div className="space-y-6 mt-6">
            {/* Profile Card */}
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
                  Update your personal information and contact details
                </p>
              </div>
              <div className="px-6 pb-4 space-y-4">
                {/* Avatar + name display */}
                <div className="flex items-center gap-4">
                  <div className="h-14 w-14 rounded-full bg-orange-500/10 flex items-center justify-center shrink-0 text-lg font-semibold text-orange-600 dark:text-orange-400 ring-2 ring-orange-500/20">
                    {initials}
                  </div>
                  <div className="space-y-1">
                    <p className="font-medium">{user?.name ?? "Operator"}</p>
                    <p className="text-sm text-muted-foreground">
                      {user?.email ?? "—"}
                    </p>
                  </div>
                </div>

                {/* Name + Email */}
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="name" className="text-sm font-medium">
                      Full Name
                    </Label>
                    <div className="relative flex items-center rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm hover:border-primary/30 focus-within:ring-2 focus-within:ring-primary/30">
                      <div className="pointer-events-none pl-3.5 text-muted-foreground/60">
                        <User className="h-4 w-4" />
                      </div>
                      <Input
                        id="name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Your name"
                        className="border-0 bg-transparent focus-visible:ring-0 pl-2"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-sm font-medium">
                      Email Address
                    </Label>
                    <div className="relative flex items-center rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm hover:border-primary/30 focus-within:ring-2 focus-within:ring-primary/30">
                      <div className="pointer-events-none pl-3.5 text-muted-foreground/60">
                        <Mail className="h-4 w-4" />
                      </div>
                      <Input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="your@email.com"
                        className="border-0 bg-transparent focus-visible:ring-0 pl-2"
                      />
                    </div>
                  </div>
                </div>

                {/* Operator-specific fields */}
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label
                      htmlFor="contactNumber"
                      className="text-sm font-medium"
                    >
                      Contact Number
                    </Label>
                    <div className="relative flex items-center rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm hover:border-primary/30 focus-within:ring-2 focus-within:ring-primary/30">
                      <div className="pointer-events-none pl-3.5 text-muted-foreground/60">
                        <Radio className="h-4 w-4" />
                      </div>
                      <Input
                        id="contactNumber"
                        value={contactNumber}
                        onChange={(e) => setContactNumber(e.target.value)}
                        placeholder="+63 9XX XXX XXXX"
                        className="border-0 bg-transparent focus-visible:ring-0 pl-2"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label
                      htmlFor="assignedArea"
                      className="text-sm font-medium"
                    >
                      Assigned Area / Zone
                    </Label>
                    <div className="relative flex items-center rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm hover:border-primary/30 focus-within:ring-2 focus-within:ring-primary/30">
                      <div className="pointer-events-none pl-3.5 text-muted-foreground/60">
                        <MapPin className="h-4 w-4" />
                      </div>
                      <Input
                        id="assignedArea"
                        value={assignedArea}
                        onChange={(e) => setAssignedArea(e.target.value)}
                        placeholder="e.g. Zone A — San Dionisio Cluster"
                        className="border-0 bg-transparent focus-visible:ring-0 pl-2"
                      />
                    </div>
                  </div>
                </div>

                {/* Role badge */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-foreground/90">
                    Role
                  </Label>
                  <div className="inline-flex items-center gap-2 rounded-xl border border-border/50 bg-muted/30 px-3.5 py-2">
                    <Shield className="h-4 w-4 text-orange-500" />
                    <span className="text-sm font-medium">LGU Operator</span>
                  </div>
                </div>
              </div>
              <div className="px-6 pb-6">
                <Button
                  onClick={handleProfileSubmit}
                  disabled={isUpdatingProfile}
                  className="rounded-xl"
                >
                  {isUpdatingProfile ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Save Changes"
                  )}
                </Button>
              </div>
            </GlassCard>

            {/* Password Card */}
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
              <div className="px-6 pb-6 space-y-4">
                {!showPwForm ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowPwForm(true)}
                    className="rounded-xl"
                  >
                    Change Password
                  </Button>
                ) : (
                  <div className="space-y-4">
                    {/* Current Password */}
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Current Password
                      </Label>
                      <div className="relative flex items-center rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm focus-within:ring-2 focus-within:ring-primary/30">
                        <div className="pointer-events-none pl-3.5 text-muted-foreground/60">
                          <Lock className="h-4 w-4" />
                        </div>
                        <Input
                          type={showCurrentPw ? "text" : "password"}
                          value={currentPw}
                          onChange={(e) => setCurrentPw(e.target.value)}
                          className="border-0 bg-transparent focus-visible:ring-0 pl-2"
                        />
                        <button
                          type="button"
                          tabIndex={-1}
                          onClick={() => setShowCurrentPw((v) => !v)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground transition-colors"
                        >
                          {showCurrentPw ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* New + Confirm */}
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">
                          New Password
                        </Label>
                        <div className="relative flex items-center rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm focus-within:ring-2 focus-within:ring-primary/30">
                          <div className="pointer-events-none pl-3.5 text-muted-foreground/60">
                            <Lock className="h-4 w-4" />
                          </div>
                          <Input
                            type={showNewPw ? "text" : "password"}
                            value={newPw}
                            onChange={(e) => setNewPw(e.target.value)}
                            className="border-0 bg-transparent focus-visible:ring-0 pl-2"
                          />
                          <button
                            type="button"
                            tabIndex={-1}
                            onClick={() => setShowNewPw((v) => !v)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground transition-colors"
                          >
                            {showNewPw ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                        {newPw.length > 0 && (
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                              <div
                                className={`h-full rounded-full ${strength.color} transition-all`}
                                style={{ width: `${strength.pct}%` }}
                              />
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {strength.label}
                            </p>
                          </div>
                        )}
                      </div>
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">
                          Confirm Password
                        </Label>
                        <div className="relative flex items-center rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm focus-within:ring-2 focus-within:ring-primary/30">
                          <div className="pointer-events-none pl-3.5 text-muted-foreground/60">
                            <Lock className="h-4 w-4" />
                          </div>
                          <Input
                            type={showConfirmPw ? "text" : "password"}
                            value={confirmPw}
                            onChange={(e) => setConfirmPw(e.target.value)}
                            className="border-0 bg-transparent focus-visible:ring-0 pl-2"
                          />
                          <button
                            type="button"
                            tabIndex={-1}
                            onClick={() => setShowConfirmPw((v) => !v)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground transition-colors"
                          >
                            {showConfirmPw ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                        {confirmPw.length > 0 && !pwMatch && (
                          <p className="text-xs text-destructive">
                            Passwords do not match
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-3 pt-1">
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-xl"
                        onClick={() => {
                          setShowPwForm(false);
                          setCurrentPw("");
                          setNewPw("");
                          setConfirmPw("");
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        className="rounded-xl"
                        disabled={
                          !currentPw ||
                          newPw.length < 8 ||
                          !pwMatch ||
                          isChangingPassword
                        }
                        onClick={handlePasswordChange}
                      >
                        {isChangingPassword ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <Lock className="h-4 w-4 mr-2" />
                        )}
                        Change Password
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </GlassCard>
          </div>
        </div>
      </section>

      {/* ── Preferences Section ───────────────────────────────────── */}
      <section className="py-10 bg-background">
        <div className="container mx-auto max-w-4xl px-4">
          <SectionHeading
            label="Preferences"
            title="Customization & Notifications"
            subtitle="Adjust theme, notification settings, and alert preferences."
          />

          <div className="space-y-6 mt-6">
            {/* Preferences Card */}
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
                    onCheckedChange={toggleTheme}
                  />
                </div>

                <Separator className="bg-border/30" />

                {/* Standard notifications */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Bell className="h-4 w-4 text-muted-foreground" />
                    <Label className="text-sm font-medium">
                      Standard Notifications
                    </Label>
                  </div>
                  <div className="space-y-3 pl-6">
                    {NOTIFICATION_ITEMS.map((notif) => (
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
                          checked={notifications[notif.key]}
                          onCheckedChange={() =>
                            handleToggleNotification(notif.key)
                          }
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <Separator className="bg-border/30" />

                {/* Operator-specific notification preferences */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Radio className="h-4 w-4 text-muted-foreground" />
                    <Label className="text-sm font-medium">
                      Operator Alert Preferences
                    </Label>
                  </div>
                  <div className="space-y-3 pl-6">
                    {OPERATOR_NOTIFICATION_ITEMS.map((notif) => (
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
                          checked={operatorNotifPrefs[notif.key]}
                          onCheckedChange={() =>
                            handleToggleOperatorNotif(notif.key)
                          }
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <Separator className="bg-border/30" />

                {/* Assigned barangays (operator-specific) */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <Label className="text-sm font-medium">
                      Alert Coverage
                    </Label>
                  </div>
                  <div className="pl-6">
                    <div className="rounded-xl border border-border/50 bg-background/50 p-3.5">
                      <p className="text-xs text-muted-foreground mb-3">
                        Select barangays you are responsible for monitoring. You
                        will receive priority alerts for these areas.
                      </p>
                      <div className="grid grid-cols-2 gap-2">
                        {BARANGAYS.map((b) => (
                          <button
                            key={b.key}
                            onClick={() =>
                              setAssignedBarangays((prev) =>
                                prev.includes(b.key)
                                  ? prev.filter((id) => id !== b.key)
                                  : [...prev, b.key],
                              )
                            }
                            className={cn(
                              "text-xs py-1.5 px-2 rounded-lg border",
                              "transition-colors text-left",
                              assignedBarangays.includes(b.key)
                                ? "bg-primary/10 border-primary/40 text-primary font-medium"
                                : "border-border/50 text-muted-foreground hover:border-border",
                            )}
                          >
                            {b.name}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </GlassCard>

            {/* Session Card */}
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
                          You will be signed out and redirected to the login
                          page. Any unsaved changes will be lost.
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
          </div>
        </div>
      </section>
    </div>
  );
}
