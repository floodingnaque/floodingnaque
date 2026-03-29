/**
 * Resident - Settings Page
 *
 * Notification preferences (synced to household profile), dark mode,
 * change-password form with strength meter, preferred language.
 */

import {
  Bell,
  Eye,
  EyeOff,
  Globe,
  Loader2,
  Lock,
  Moon,
  Save,
  Sun,
  User,
} from "lucide-react";
import { useCallback, useState } from "react";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useAuth } from "@/features/auth";
import {
  useHouseholdProfile,
  useUpdateHouseholdProfile,
} from "@/features/resident";
import { showToast } from "@/lib/toast";
import { useLanguage, useTheme, useUIActions, useUser } from "@/state";

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

export default function ResidentSettingsPage() {
  const user = useUser();
  const theme = useTheme();
  const language = useLanguage();
  const { toggleTheme, setLanguage } = useUIActions();
  const { data: household } = useHouseholdProfile();
  const updateProfile = useUpdateHouseholdProfile();
  const { changePassword, isChangingPassword } = useAuth();

  // ── Notification prefs (synced to profile) ─────────────────────
  const [smsAlerts, setSmsAlerts] = useState(household?.sms_alerts ?? true);
  const [emailAlerts, setEmailAlerts] = useState(
    household?.email_alerts ?? true,
  );
  const [pushAlerts, setPushAlerts] = useState(
    household?.push_notifications ?? true,
  );

  // ── Password change form ───────────────────────────────────────
  const [showPwForm, setShowPwForm] = useState(false);
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showPw, setShowPw] = useState(false);

  const strength = passwordStrength(newPw);
  const pwMatch = newPw === confirmPw;

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((w) => w[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "?";

  // ── Save notification prefs to server ──────────────────────────
  const handleSavePrefs = useCallback(() => {
    updateProfile.mutate({
      sms_alerts: smsAlerts,
      email_alerts: emailAlerts,
      push_notifications: pushAlerts,
      preferred_language: language,
    });
  }, [smsAlerts, emailAlerts, pushAlerts, language, updateProfile]);

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

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      <Breadcrumb
        items={[{ label: "Home", href: "/resident" }, { label: "Settings" }]}
        className="mb-4"
      />

      {/* ── Profile ───────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <User className="h-4 w-4 text-primary" />
            {language === "fil" ? "Aking Account / My Account" : "My Account"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarFallback className="text-lg">{initials}</AvatarFallback>
            </Avatar>
            <div>
              <p className="font-medium">{user?.name ?? "Resident"}</p>
              <p className="text-sm text-muted-foreground">
                {user?.email ?? "-"}
              </p>
              <Badge variant="outline" className="mt-1 text-xs">
                Resident
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Appearance ────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            {theme === "dark" ? (
              <Moon className="h-4 w-4" />
            ) : (
              <Sun className="h-4 w-4" />
            )}
            {language === "fil" ? "Anyo / Appearance" : "Appearance"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Dark Mode</p>
              <p className="text-xs text-muted-foreground">
                {language === "fil"
                  ? "Gabi mode para sa mata"
                  : "Reduce eye strain at night"}
              </p>
            </div>
            <Switch checked={theme === "dark"} onCheckedChange={toggleTheme} />
          </div>
        </CardContent>
      </Card>

      {/* ── Language ──────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Globe className="h-4 w-4 text-primary" />
            {language === "fil" ? "Wika / Language" : "Language"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            {[
              { code: "fil" as const, label: "Filipino" },
              { code: "en" as const, label: "English" },
            ].map(({ code, label }) => (
              <Button
                key={code}
                size="sm"
                variant={language === code ? "default" : "outline"}
                onClick={() => setLanguage(code)}
              >
                {label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ── Notifications ─────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4 text-primary" />
            {language === "fil" ? "Mga Abiso / Notifications" : "Notifications"}
          </CardTitle>
          <CardDescription>
            {language === "fil"
              ? "Paano mo gustong makatanggap ng flood alerts"
              : "How you want to receive flood alerts"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Push Notifications</p>
              <p className="text-xs text-muted-foreground">
                Critical alerts on your device
              </p>
            </div>
            <Switch checked={pushAlerts} onCheckedChange={setPushAlerts} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">SMS Alerts</p>
              <p className="text-xs text-muted-foreground">
                Text message flood warnings
              </p>
            </div>
            <Switch checked={smsAlerts} onCheckedChange={setSmsAlerts} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Email Alerts</p>
              <p className="text-xs text-muted-foreground">
                Flood updates via email
              </p>
            </div>
            <Switch checked={emailAlerts} onCheckedChange={setEmailAlerts} />
          </div>

          <Button
            size="sm"
            className="gap-2"
            onClick={handleSavePrefs}
            disabled={updateProfile.isPending}
          >
            {updateProfile.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save Preferences
          </Button>
        </CardContent>
      </Card>

      {/* ── Security ──────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Lock className="h-4 w-4 text-primary" />
            {language === "fil" ? "Seguridad / Security" : "Security"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {!showPwForm ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPwForm(true)}
            >
              Change Password
            </Button>
          ) : (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <p className="text-sm font-medium">Current Password</p>
                <div className="relative">
                  <Input
                    type={showPw ? "text" : "password"}
                    value={currentPw}
                    onChange={(e) => setCurrentPw(e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute top-0 right-0 h-full px-3"
                    onClick={() => setShowPw((v) => !v)}
                  >
                    {showPw ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
              <div className="space-y-1.5">
                <p className="text-sm font-medium">New Password</p>
                <Input
                  type={showPw ? "text" : "password"}
                  value={newPw}
                  onChange={(e) => setNewPw(e.target.value)}
                />
                {newPw.length > 0 && (
                  <div className="space-y-1">
                    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${strength.color}`}
                        style={{ width: `${strength.pct}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {strength.label}
                    </p>
                  </div>
                )}
              </div>
              <div className="space-y-1.5">
                <p className="text-sm font-medium">Confirm New Password</p>
                <Input
                  type={showPw ? "text" : "password"}
                  value={confirmPw}
                  onChange={(e) => setConfirmPw(e.target.value)}
                />
                {confirmPw.length > 0 && !pwMatch && (
                  <p className="text-xs text-destructive">
                    Passwords do not match
                  </p>
                )}
              </div>
              <div className="flex gap-3 pt-1">
                <Button
                  variant="outline"
                  size="sm"
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
                  ) : null}
                  Update Password
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
