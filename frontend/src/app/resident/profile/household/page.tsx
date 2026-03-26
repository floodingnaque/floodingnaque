/**
 * Resident - My Household Page
 *
 * Real API integration via useHouseholdProfile & useUpdateHouseholdProfile.
 * Section-based editing with profile completeness indicator.
 */

import {
  CheckCircle,
  Droplets,
  Heart,
  Loader2,
  MapPin,
  Save,
  Users,
} from "lucide-react";
import { useCallback, useState } from "react";

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
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  useHouseholdProfile,
  useUpdateHouseholdProfile,
} from "@/features/resident";
import type {
  HouseholdProfile,
  HouseholdProfileUpdate,
} from "@/features/resident/services/residentApi";
import { useUser } from "@/state";

function profileToForm(h: Partial<HouseholdProfile>): HouseholdProfileUpdate {
  return {
    contact_number: h.contact_number ?? "",
    alt_contact_number: h.alt_contact_number ?? "",
    alt_contact_name: h.alt_contact_name ?? "",
    alt_contact_relationship: h.alt_contact_relationship ?? "",
    is_pwd: h.is_pwd ?? false,
    is_senior_citizen: h.is_senior_citizen ?? false,
    household_members: h.household_members ?? undefined,
    children_count: h.children_count ?? 0,
    senior_count: h.senior_count ?? 0,
    pwd_count: h.pwd_count ?? 0,
    barangay: h.barangay ?? "",
    purok: h.purok ?? "",
    street_address: h.street_address ?? "",
    nearest_landmark: h.nearest_landmark ?? "",
    home_type: h.home_type ?? "",
    floor_level: h.floor_level ?? undefined,
    has_flood_experience: h.has_flood_experience ?? false,
    most_recent_flood_year: h.most_recent_flood_year ?? undefined,
  };
}

function computeCompleteness(data: HouseholdProfileUpdate): number {
  const required: (keyof HouseholdProfileUpdate)[] = [
    "barangay",
    "street_address",
    "contact_number",
    "household_members",
    "home_type",
  ];
  let filled = 0;
  for (const f of required) {
    if (data[f]) filled++;
  }
  return Math.round((filled / required.length) * 100);
}

export default function ResidentHouseholdPage() {
  const user = useUser();
  const { data: household, isLoading } = useHouseholdProfile();
  const updateMutation = useUpdateHouseholdProfile();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<HouseholdProfileUpdate>({});

  const form = editing ? draft : profileToForm(household ?? {});

  const startEditing = useCallback(() => {
    setDraft(profileToForm(household ?? {}));
    setEditing(true);
  }, [household]);

  const cancelEditing = useCallback(() => setEditing(false), []);

  const handleSave = useCallback(() => {
    updateMutation.mutate(draft, { onSuccess: () => setEditing(false) });
  }, [draft, updateMutation]);

  const completeness = computeCompleteness(form);

  if (isLoading) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-64 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      {/* ── Header + Completeness ─────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Heart className="h-5 w-5 text-red-500" />
            Ang Aking Sambahayan / My Household
          </h2>
          <p className="text-sm text-muted-foreground">
            Ilagay ang impormasyon ng sambahayan para sa emergency tracking
          </p>
        </div>
        <Badge
          variant={completeness >= 80 ? "default" : "outline"}
          className="self-start"
        >
          {completeness >= 80 && <CheckCircle className="h-3 w-3 mr-1" />}
          {completeness}% complete
        </Badge>
      </div>

      {/* ── Completeness Bar ──────────────────────────────────────── */}
      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            completeness >= 80
              ? "bg-green-500"
              : completeness >= 40
                ? "bg-amber-500"
                : "bg-red-500"
          }`}
          style={{ width: `${completeness}%` }}
        />
      </div>

      {/* ── Location ──────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <MapPin className="h-4 w-4 text-primary" />
            Lokasyon / Location
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Head of Household</p>
              <Input value={user?.name ?? ""} readOnly />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Barangay</p>
              <Input
                placeholder="Your barangay"
                readOnly={!editing}
                value={form.barangay ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({ ...p, barangay: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Purok / Zone</p>
              <Input
                placeholder="Purok number"
                readOnly={!editing}
                value={form.purok ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({ ...p, purok: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Street Address</p>
              <Input
                placeholder="House/Block/Lot, Street"
                readOnly={!editing}
                value={form.street_address ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({ ...p, street_address: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Nearest Landmark</p>
              <Input
                placeholder="e.g. near sari-sari store"
                readOnly={!editing}
                value={form.nearest_landmark ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({ ...p, nearest_landmark: e.target.value }))
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Contact ───────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Kontak / Contact Information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Contact Number</p>
              <Input
                placeholder="09XX-XXX-XXXX"
                readOnly={!editing}
                value={form.contact_number ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({ ...p, contact_number: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Emergency Contact Name</p>
              <Input
                placeholder="Name"
                readOnly={!editing}
                value={form.alt_contact_name ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({ ...p, alt_contact_name: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Emergency Contact Number</p>
              <Input
                placeholder="09XX-XXX-XXXX"
                readOnly={!editing}
                value={form.alt_contact_number ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    alt_contact_number: e.target.value,
                  }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Relationship</p>
              <Input
                placeholder="e.g. Kapatid, Magulang"
                readOnly={!editing}
                value={form.alt_contact_relationship ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    alt_contact_relationship: e.target.value,
                  }))
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Household Members ─────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            Mga Kasambahay / Household Members
          </CardTitle>
          <CardDescription>
            Makakatulong sa MDRRMO na mag-prioritize ng tulong
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Total Members</p>
              <Input
                type="number"
                min={1}
                max={50}
                readOnly={!editing}
                value={form.household_members ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    household_members: parseInt(e.target.value) || undefined,
                  }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Children (0-12)</p>
              <Input
                type="number"
                min={0}
                readOnly={!editing}
                value={form.children_count ?? 0}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    children_count: parseInt(e.target.value) || 0,
                  }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Seniors (60+)</p>
              <Input
                type="number"
                min={0}
                readOnly={!editing}
                value={form.senior_count ?? 0}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    senior_count: parseInt(e.target.value) || 0,
                  }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">PWD Count</p>
              <Input
                type="number"
                min={0}
                readOnly={!editing}
                value={form.pwd_count ?? 0}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    pwd_count: parseInt(e.target.value) || 0,
                  }))
                }
              />
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between p-3 rounded-lg border border-border/50">
              <div>
                <p className="text-sm font-medium">Senior Citizen (60+)</p>
                <p className="text-xs text-muted-foreground">
                  Matatanda sa bahay
                </p>
              </div>
              <Switch
                disabled={!editing}
                checked={!!form.is_senior_citizen}
                onCheckedChange={(val) =>
                  setDraft((p) => ({ ...p, is_senior_citizen: val }))
                }
              />
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg border border-border/50">
              <div>
                <p className="text-sm font-medium">Person with Disability</p>
                <p className="text-xs text-muted-foreground">
                  Taong may kapansanan
                </p>
              </div>
              <Switch
                disabled={!editing}
                checked={!!form.is_pwd}
                onCheckedChange={(val) =>
                  setDraft((p) => ({ ...p, is_pwd: val }))
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Home & Flood Experience ───────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Droplets className="h-4 w-4 text-blue-500" />
            Bahay at Karanasan sa Baha / Home & Flood Experience
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Home Type</p>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!editing}
                value={form.home_type ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    home_type: e.target.value || undefined,
                  }))
                }
              >
                <option value="">Select home type</option>
                <option value="Concrete">Concrete</option>
                <option value="Semi-Concrete">Semi-Concrete</option>
                <option value="Wood">Wood</option>
                <option value="Makeshift">Makeshift</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Floor Level</p>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!editing}
                value={form.floor_level ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    floor_level: e.target.value || undefined,
                  }))
                }
              >
                <option value="">Select floor level</option>
                <option value="Ground Floor">Ground Floor</option>
                <option value="2nd Floor">2nd Floor</option>
                <option value="3rd Floor or higher">3rd Floor or higher</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg border border-border/50">
            <div>
              <p className="text-sm font-medium">Has Flood Experience</p>
              <p className="text-xs text-muted-foreground">
                Nakaranas na ba ng baha ang bahay?
              </p>
            </div>
            <Switch
              disabled={!editing}
              checked={!!form.has_flood_experience}
              onCheckedChange={(val) =>
                setDraft((p) => ({ ...p, has_flood_experience: val }))
              }
            />
          </div>

          {form.has_flood_experience && (
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Most Recent Flood Year</p>
              <Input
                type="number"
                min={2000}
                max={2030}
                placeholder="e.g. 2024"
                readOnly={!editing}
                value={form.most_recent_flood_year ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    most_recent_flood_year:
                      parseInt(e.target.value) || undefined,
                  }))
                }
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Action Buttons ────────────────────────────────────────── */}
      <div className="flex gap-3">
        {editing ? (
          <>
            <Button variant="outline" onClick={cancelEditing}>
              Cancel
            </Button>
            <Button
              className="gap-2"
              onClick={handleSave}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save Changes
            </Button>
          </>
        ) : (
          <Button variant="outline" onClick={startEditing}>
            Edit Profile
          </Button>
        )}
      </div>
    </div>
  );
}
