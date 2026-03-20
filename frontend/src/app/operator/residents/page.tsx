/**
 * Operator — Resident Registry Page
 */

import { Search, UserCheck, Users } from "lucide-react";
import { useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function OperatorResidentsPage() {
  const [search, setSearch] = useState("");

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">0</p>
            <p className="text-xs text-muted-foreground">Registered</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-green-600">0</p>
            <p className="text-xs text-muted-foreground">Safe</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-red-600">0</p>
            <p className="text-xs text-muted-foreground">Evacuated</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-amber-600">0</p>
            <p className="text-xs text-muted-foreground">Vulnerable</p>
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
            Search residents, view vulnerability status, and manage records
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-10"
              placeholder="Search by name, barangay, or household ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Empty state */}
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <UserCheck className="h-10 w-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">No residents registered</p>
            <p className="text-xs mt-1">
              Resident records will populate as users create accounts
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
