/**
 * ReportSubmitModal Component
 *
 * Slide-up sheet for submitting a crowdsourced flood report.
 * Includes barangay selection, location picker, flood severity,
 * water level, description, photo upload, contact number,
 * and risk level radio buttons.
 */

import { Camera, Check, Loader2, MapPin, Waves, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { BARANGAYS } from "@/config/paranaque";
import { cn } from "@/lib/utils";
import { FLOOD_HEIGHT_OPTIONS } from "@/types";
import { useSubmitReport } from "../hooks/useCommunityReports";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ReportSubmitModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_PHOTO_SIZE = 5 * 1024 * 1024; // 5 MB
const MAX_DESCRIPTION_LENGTH = 280;
const ACCEPTED_IMAGE_TYPES = "image/jpeg,image/png,image/webp";

const RISK_OPTIONS = [
  { value: "Safe", color: "bg-risk-safe", ring: "ring-risk-safe" },
  { value: "Alert", color: "bg-risk-alert", ring: "ring-risk-alert" },
  { value: "Critical", color: "bg-risk-critical", ring: "ring-risk-critical" },
] as const;

const SEVERITY_OPTIONS = [
  { value: "Low", label: "Low", description: "Minor surface water" },
  { value: "Moderate", label: "Moderate", description: "Ankle to knee-deep" },
  { value: "Severe", label: "Severe", description: "Knee to waist-deep" },
  { value: "Critical", label: "Critical", description: "Above waist-deep" },
] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ReportSubmitModal({
  open,
  onOpenChange,
}: ReportSubmitModalProps) {
  // ── Form state ──
  const [lat, setLat] = useState<number | null>(null);
  const [lon, setLon] = useState<number | null>(null);
  const [selectedBarangay, setSelectedBarangay] = useState<string>("");
  const [specificLocation, setSpecificLocation] = useState("");
  const [floodHeight, setFloodHeight] = useState<string>("");
  const [severity, setSeverity] = useState<string>("");
  const [description, setDescription] = useState("");
  const [contactNumber, setContactNumber] = useState("");
  const [riskLabel, setRiskLabel] = useState<string>("Alert");
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [geoLoading, setGeoLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const fileInputRef = useRef<HTMLInputElement>(null);
  const submitMutation = useSubmitReport();

  // ── Validation ──
  const validate = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};
    if (lat === null || lon === null) {
      newErrors.location = "Please set your location first";
    }
    if (!selectedBarangay) {
      newErrors.barangay = "Please select a barangay";
    }
    if (contactNumber && !/^[0-9+\-\s()]{7,20}$/.test(contactNumber.trim())) {
      newErrors.contact = "Enter a valid phone number";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [lat, lon, selectedBarangay, contactNumber]);

  // ── Location handling ──
  const handleUseMyLocation = useCallback(() => {
    if (!navigator.geolocation) {
      toast.error("Geolocation is not supported by your browser");
      return;
    }
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLon(pos.coords.longitude);
        setGeoLoading(false);
        toast.success("Location detected");
      },
      (err) => {
        setGeoLoading(false);
        toast.error(`Location error: ${err.message}`);
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }, []);

  // ── Photo handling ──
  const handlePhotoSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (file.size > MAX_PHOTO_SIZE) {
        toast.error("Photo must be under 5 MB");
        return;
      }
      setPhotoFile(file);
      setPhotoPreview(URL.createObjectURL(file));
    },
    [],
  );

  const clearPhoto = useCallback(() => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoFile(null);
    setPhotoPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [photoPreview]);

  // ── Reset form ──
  const resetForm = useCallback(() => {
    setLat(null);
    setLon(null);
    setSelectedBarangay("");
    setSpecificLocation("");
    setFloodHeight("");
    setSeverity("");
    setDescription("");
    setContactNumber("");
    setRiskLabel("Alert");
    setSubmitted(false);
    setErrors({});
    clearPhoto();
  }, [clearPhoto]);

  // ── Submit ──
  const handleSubmit = useCallback(() => {
    if (!validate()) return;

    const formData = new FormData();
    formData.append("latitude", lat!.toString());
    formData.append("longitude", lon!.toString());
    formData.append("risk_label", riskLabel);
    formData.append("barangay", selectedBarangay);

    if (specificLocation.trim()) {
      formData.append("specific_location", specificLocation.trim());
    }

    const selectedHeight = FLOOD_HEIGHT_OPTIONS.find(
      (o) => o.label === floodHeight,
    );
    if (selectedHeight?.value != null) {
      formData.append("flood_height_cm", selectedHeight.value.toString());
    }
    if (description.trim()) {
      formData.append("description", description.trim());
    }
    if (contactNumber.trim()) {
      formData.append("contact_number", contactNumber.trim());
    }
    if (photoFile) {
      formData.append("photo", photoFile);
    }

    submitMutation.mutate(formData, {
      onSuccess: () => {
        setSubmitted(true);
      },
      onError: () => {
        toast.error("Failed to submit report — please try again");
      },
    });
  }, [
    lat,
    lon,
    riskLabel,
    selectedBarangay,
    specificLocation,
    floodHeight,
    description,
    contactNumber,
    photoFile,
    submitMutation,
    validate,
  ]);

  // ── Reset on close ──
  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        resetForm();
      }
      onOpenChange(nextOpen);
    },
    [onOpenChange, resetForm],
  );

  // ── Confirmation state after successful submit ──
  if (submitted) {
    return (
      <Sheet open={open} onOpenChange={handleOpenChange}>
        <SheetContent
          side="right"
          className="w-full sm:max-w-md overflow-y-auto bg-background/95 backdrop-blur-xl"
        >
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-risk-safe/15">
              <Check className="h-8 w-8 text-risk-safe" />
            </div>
            <h3 className="text-lg font-semibold">Report Submitted</h3>
            <p className="text-sm text-muted-foreground max-w-xs">
              Thank you! Your flood report has been submitted and will be
              reviewed by our verification system.
            </p>
            <Button
              className="mt-4"
              onClick={() => {
                resetForm();
                onOpenChange(false);
              }}
            >
              Close
            </Button>
          </div>
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-md overflow-y-auto bg-background/95 backdrop-blur-xl"
      >
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Waves className="h-5 w-5 text-blue-500" />
            Report Flood
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-5">
          {/* ── Location ── */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Location</Label>
            <Button
              variant="outline"
              className="w-full justify-start gap-2"
              onClick={handleUseMyLocation}
              disabled={geoLoading}
            >
              {geoLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <MapPin className="h-4 w-4" />
              )}
              {lat !== null
                ? `${lat.toFixed(5)}, ${lon?.toFixed(5)}`
                : "Use my location"}
            </Button>
            {errors.location && (
              <p className="text-xs text-destructive">{errors.location}</p>
            )}
          </div>

          {/* ── Barangay ── */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Barangay</Label>
            <Select
              value={selectedBarangay}
              onValueChange={setSelectedBarangay}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select barangay" />
              </SelectTrigger>
              <SelectContent>
                {BARANGAYS.map((b) => (
                  <SelectItem key={b.key} value={b.name}>
                    {b.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.barangay && (
              <p className="text-xs text-destructive">{errors.barangay}</p>
            )}
          </div>

          {/* ── Specific Location ── */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">
              Landmark / Street{" "}
              <span className="text-muted-foreground font-normal">
                (optional)
              </span>
            </Label>
            <Input
              value={specificLocation}
              onChange={(e) =>
                setSpecificLocation(e.target.value.slice(0, 200))
              }
              placeholder="e.g. Near Olivarez Plaza, Dr. A. Santos Ave."
              maxLength={200}
            />
          </div>

          {/* ── Flood Severity ── */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Flood Severity</Label>
            <Select value={severity} onValueChange={setSeverity}>
              <SelectTrigger>
                <SelectValue placeholder="Select severity" />
              </SelectTrigger>
              <SelectContent>
                {SEVERITY_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}{" "}
                    <span className="text-muted-foreground">
                      — {opt.description}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* ── Water Level ── */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Water Level Estimate</Label>
            <Select value={floodHeight} onValueChange={setFloodHeight}>
              <SelectTrigger>
                <SelectValue placeholder="Select water level" />
              </SelectTrigger>
              <SelectContent>
                {FLOOD_HEIGHT_OPTIONS.map((opt) => (
                  <SelectItem key={opt.label} value={opt.label}>
                    {opt.label}{" "}
                    <span className="text-muted-foreground">
                      ({opt.description})
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* ── Description ── */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Description</Label>
              <span
                className={cn(
                  "text-xs",
                  description.length > MAX_DESCRIPTION_LENGTH
                    ? "text-destructive"
                    : "text-muted-foreground",
                )}
              >
                {description.length}/{MAX_DESCRIPTION_LENGTH}
              </span>
            </div>
            <textarea
              value={description}
              onChange={(e) =>
                setDescription(e.target.value.slice(0, MAX_DESCRIPTION_LENGTH))
              }
              placeholder="Describe the flood situation..."
              rows={3}
              className={cn(
                "flex w-full rounded-md border border-input bg-background px-3 py-2",
                "text-sm ring-offset-background placeholder:text-muted-foreground",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                "focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
                "resize-none",
              )}
            />
          </div>

          {/* ── Photo Upload ── */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Photo (optional)</Label>
            {photoPreview ? (
              <div className="relative">
                <img
                  src={photoPreview}
                  alt="Preview"
                  className="w-full rounded-lg object-cover max-h-48"
                  loading="lazy"
                  decoding="async"
                  width={500}
                  height={300}
                />
                <Button
                  size="icon"
                  variant="destructive"
                  className="absolute top-2 right-2 h-7 w-7 rounded-full"
                  onClick={clearPhoto}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <Button
                variant="outline"
                className="w-full justify-start gap-2"
                onClick={() => fileInputRef.current?.click()}
              >
                <Camera className="h-4 w-4" />
                Add photo
              </Button>
            )}
            <Input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_IMAGE_TYPES}
              className="hidden"
              onChange={handlePhotoSelect}
            />
          </div>

          {/* ── Contact Number ── */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">
              Contact Number{" "}
              <span className="text-muted-foreground font-normal">
                (optional)
              </span>
            </Label>
            <Input
              value={contactNumber}
              onChange={(e) => setContactNumber(e.target.value)}
              placeholder="e.g. 09171234567"
              maxLength={20}
              type="tel"
            />
            {errors.contact && (
              <p className="text-xs text-destructive">{errors.contact}</p>
            )}
          </div>

          {/* ── Risk Level ── */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Risk Level</Label>
            <div className="flex gap-2">
              {RISK_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setRiskLabel(opt.value)}
                  className={cn(
                    "flex-1 rounded-lg border-2 py-2.5 text-sm font-medium transition-all",
                    riskLabel === opt.value
                      ? `${opt.ring} ring-2 ring-offset-2 ring-offset-background border-transparent ${opt.color} text-white`
                      : "border-border hover:border-foreground/20",
                  )}
                >
                  {opt.value}
                </button>
              ))}
            </div>
          </div>

          {/* ── Submit Button ── */}
          <Button
            className="w-full"
            size="lg"
            onClick={handleSubmit}
            disabled={submitMutation.isPending || lat === null}
          >
            {submitMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Submitting…
              </>
            ) : (
              "Submit Report"
            )}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
