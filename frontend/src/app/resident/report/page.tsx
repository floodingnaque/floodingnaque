/**
 * Resident - Report Flood Page
 *
 * Large tappable severity tiles, location input, description,
 * photo upload with preview, "people in danger" toggle,
 * submission progress, and confirmation screen.
 */

import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Droplets,
  Loader2,
  MapPin,
  Send,
  Users,
  X,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
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
import { Textarea } from "@/components/ui/textarea";
import { useSubmitReport } from "@/features/resident";

/* ── Severity tile data ───────────────────────────────────────────────── */

const SEVERITIES = [
  {
    value: "minor",
    emoji: "",
    label: "Minor",
    labelFil: "Mababaw",
    desc: "Ankle-deep, passable on foot",
    height: "0–15 cm",
    riskLabel: "Safe" as const,
    color:
      "border-green-500/50 bg-green-500/10 text-green-700 dark:text-green-400",
    selectedColor: "border-green-500 bg-green-500/20 ring-2 ring-green-500/40",
  },
  {
    value: "moderate",
    emoji: "",
    label: "Moderate",
    labelFil: "Katamtaman",
    desc: "Knee-deep, difficult to walk",
    height: "15–60 cm",
    riskLabel: "Alert" as const,
    color:
      "border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-400",
    selectedColor: "border-amber-500 bg-amber-500/20 ring-2 ring-amber-500/40",
  },
  {
    value: "severe",
    emoji: "",
    label: "Severe",
    labelFil: "Malala",
    desc: "Waist-deep or higher, impassable",
    height: "60+ cm",
    riskLabel: "Critical" as const,
    color: "border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-400",
    selectedColor: "border-red-500 bg-red-500/20 ring-2 ring-red-500/40",
  },
] as const;

type SeverityValue = (typeof SEVERITIES)[number]["value"];

export default function ResidentReportPage() {
  const navigate = useNavigate();
  const submitMutation = useSubmitReport();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [severity, setSeverity] = useState<SeverityValue>("moderate");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [waterLevel, setWaterLevel] = useState("");
  const [peopleDanger, setPeopleDanger] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const handlePhoto = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhoto(file);
    const reader = new FileReader();
    reader.onloadend = () => setPhotoPreview(reader.result as string);
    reader.readAsDataURL(file);
  }, []);

  const removePhoto = useCallback(() => {
    setPhoto(null);
    setPhotoPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  const handleSubmit = useCallback(() => {
    const selected = SEVERITIES.find((s) => s.value === severity);
    const formData = new FormData();
    formData.append("risk_label", selected?.riskLabel ?? "Alert");
    formData.append("location", location);
    formData.append("description", description);
    if (waterLevel) formData.append("flood_height_cm", waterLevel);
    if (peopleDanger) formData.append("people_in_danger", "true");
    if (photo) formData.append("photo", photo);

    submitMutation.mutate(formData, {
      onSuccess: () => setSubmitted(true),
    });
  }, [
    severity,
    location,
    description,
    waterLevel,
    peopleDanger,
    photo,
    submitMutation,
  ]);

  const canSubmit = location.trim().length > 0 && description.trim().length > 0;

  /* ── Confirmation screen ─────────────────────────────────────────── */
  if (submitted) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 w-full">
        <Breadcrumb
          items={[
            { label: "Home", href: "/resident" },
            { label: "Report Flooding" },
          ]}
          className="mb-4"
        />
        <Card className="max-w-lg mx-auto">
          <CardContent className="flex flex-col items-center py-12 text-center">
            <div className="h-16 w-16 rounded-full bg-green-500/10 flex items-center justify-center mb-4">
              <CheckCircle2 className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-xl font-semibold">
              Naipadala na! / Report Submitted
            </h3>
            <p className="text-sm text-muted-foreground mt-2 max-w-sm">
              Thank you for helping keep Parañaque safe. An MDRRMO operator will
              verify your report shortly.
            </p>
            <div className="flex gap-3 mt-6">
              <Button asChild variant="outline">
                <Link to="/resident/my-reports">View My Reports</Link>
              </Button>
              <Button onClick={() => navigate("/resident")}>Back Home</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      <Breadcrumb
        items={[
          { label: "Home", href: "/resident" },
          { label: "Report Flooding" },
        ]}
        className="mb-4"
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            Mag-ulat ng Baha / Report Flooding
          </CardTitle>
          <CardDescription>
            Help your community - your report will be verified by MDRRMO
            operators.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* ── Severity Tiles ─────────────────────────────────────── */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Gaano kalala? / How severe?</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {SEVERITIES.map((s) => (
                <button
                  key={s.value}
                  type="button"
                  onClick={() => setSeverity(s.value)}
                  className={`flex flex-col items-center gap-1.5 p-4 rounded-xl border-2 transition-all active:scale-[0.97] ${
                    severity === s.value ? s.selectedColor : s.color
                  }`}
                >
                  <span className="text-2xl">{s.emoji}</span>
                  <span className="text-sm font-semibold">{s.label}</span>
                  <span className="text-[10px] text-muted-foreground">
                    {s.labelFil}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {s.height}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* ── Location ───────────────────────────────────────────── */}
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Lokasyon / Location *</p>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                className="pl-10"
                placeholder="Street, barangay, or landmark…"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
          </div>

          {/* ── Water Level ────────────────────────────────────────── */}
          <div className="space-y-1.5">
            <p className="text-sm font-medium">
              Taas ng tubig / Water level (cm)
            </p>
            <div className="relative">
              <Droplets className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                className="pl-10"
                placeholder="e.g., 30"
                type="number"
                min={0}
                max={500}
                value={waterLevel}
                onChange={(e) => setWaterLevel(e.target.value)}
              />
            </div>
          </div>

          {/* ── Description ────────────────────────────────────────── */}
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Deskripsyon / Description *</p>
            <Textarea
              placeholder="Describe the flood - is water rising fast? Are people stranded? Is the road passable?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
            />
          </div>

          {/* ── People in Danger Toggle ────────────────────────────── */}
          <div className="flex items-center justify-between p-4 rounded-xl border-2 border-red-500/30 bg-red-500/5">
            <div className="flex items-center gap-3">
              <Users className="h-5 w-5 text-red-600 shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-700 dark:text-red-400">
                  May mga tao sa panganib? / People in danger?
                </p>
                <p className="text-xs text-muted-foreground">
                  This will flag the report as urgent
                </p>
              </div>
            </div>
            <Switch checked={peopleDanger} onCheckedChange={setPeopleDanger} />
          </div>

          {/* ── Photo Upload ───────────────────────────────────────── */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Larawan / Photo (Optional)</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={handlePhoto}
            />
            {photoPreview ? (
              <div className="relative inline-block">
                <img
                  src={photoPreview}
                  alt="Flood report preview"
                  className="h-32 w-auto rounded-lg border object-cover"
                />
                <button
                  type="button"
                  onClick={removePhoto}
                  className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ) : (
              <Button
                type="button"
                variant="outline"
                className="gap-2"
                onClick={() => fileInputRef.current?.click()}
              >
                <Camera className="h-4 w-4" />
                Take or Choose Photo
              </Button>
            )}
          </div>

          {/* ── Submit ─────────────────────────────────────────────── */}
          <Button
            className="w-full gap-2"
            disabled={!canSubmit || submitMutation.isPending}
            onClick={handleSubmit}
          >
            {submitMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Submitting…
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Ipadala / Submit Report
              </>
            )}
          </Button>

          {!canSubmit && (
            <p className="text-xs text-muted-foreground text-center">
              Please fill in location and description to submit
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
