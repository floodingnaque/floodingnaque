/**
 * Operator - Resident Registry Page
 *
 * Directory of registered residents with search, barangay filtering,
 * and summary stats.
 */

import { Clock, MapPin, Search, UserCheck, Users } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useResidents } from "@/features/operator";

const PARANAQUE_BARANGAYS = [
  "Baclaran",
  "BF Homes",
  "Don Bosco",
  "Don Galo",
  "La Huerta",
  "Merville",
  "Moonwalk",
  "San Antonio",
  "San Dionisio",
  "San Isidro",
  "San Martin de Porres",
  "Santo Niño",
  "Sun Valley",
  "Tambo",
  "Vitalez",
  "Sucat",
];

interface ResidentUser {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  first_name?: string;
  last_name?: string;
  barangay?: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export default function OperatorResidentsPage() {
  const [search, setSearch] = useState("");
  const [barangayFilter, setBarangayFilter] = useState("all");

  const { data: residentsData, isLoading } = useResidents();

  const residents: ResidentUser[] = useMemo(() => {
    if (!residentsData) return [];
    if (Array.isArray(residentsData)) return residentsData;
    if (typeof residentsData === "object" && "data" in residentsData) {
      return (residentsData as unknown as { data: ResidentUser[] }).data ?? [];
    }
    return [];
  }, [residentsData]);

  const filtered = useMemo(() => {
    let result = residents;
    if (barangayFilter !== "all") {
      result = result.filter((r) => r.barangay === barangayFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (r) =>
          r.username?.toLowerCase().includes(q) ||
          (r.full_name ?? `${r.first_name ?? ""} ${r.last_name ?? ""}`)
            .toLowerCase()
            .includes(q) ||
          r.email?.toLowerCase().includes(q) ||
          r.barangay?.toLowerCase().includes(q),
      );
    }
    return result;
  }, [residents, barangayFilter, search]);

  const barangayCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of residents) {
      if (r.barangay) counts[r.barangay] = (counts[r.barangay] ?? 0) + 1;
    }
    return counts;
  }, [residents]);

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{residents.length}</p>
            <p className="text-xs text-muted-foreground">Registered</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-green-600">
              {residents.filter((r) => r.is_active).length}
            </p>
            <p className="text-xs text-muted-foreground">Active</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-blue-600">
              {Object.keys(barangayCounts).length}
            </p>
            <p className="text-xs text-muted-foreground">Barangays</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-amber-600">
              {residents.filter((r) => !r.is_active).length}
            </p>
            <p className="text-xs text-muted-foreground">Inactive</p>
          </CardContent>
        </Card>
      </div>

      {/* Directory */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            Resident Directory
          </CardTitle>
          <CardDescription>
            Search residents, view status, and filter by barangay
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                className="pl-10"
                placeholder="Search by name, email, or barangay…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={barangayFilter} onValueChange={setBarangayFilter}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Barangay" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Barangays</SelectItem>
                {PARANAQUE_BARANGAYS.map((b) => (
                  <SelectItem key={b} value={b}>
                    {b} {barangayCounts[b] ? `(${barangayCounts[b]})` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded-lg" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <UserCheck className="h-10 w-10 mb-3 opacity-30" />
              <p className="text-sm font-medium">
                {search || barangayFilter !== "all"
                  ? "No residents match your filters"
                  : "No residents registered"}
              </p>
              <p className="text-xs mt-1">
                Resident records will populate as users create accounts
              </p>
            </div>
          ) : (
            <div className="divide-y">
              {filtered.map((resident) => (
                <div
                  key={resident.id}
                  className="flex items-center justify-between gap-4 py-3 px-1"
                >
                  <div className="space-y-0.5 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {resident.full_name ??
                        (`${resident.first_name ?? ""} ${resident.last_name ?? ""}`.trim() ||
                          resident.username)}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>{resident.email}</span>
                      {resident.barangay && (
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {resident.barangay}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(resident.created_at).toLocaleDateString(
                          "en-PH",
                          { month: "short", day: "numeric", year: "numeric" },
                        )}
                      </span>
                    </div>
                  </div>
                  <Badge
                    variant={resident.is_active ? "default" : "secondary"}
                    className="text-xs shrink-0"
                  >
                    {resident.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
