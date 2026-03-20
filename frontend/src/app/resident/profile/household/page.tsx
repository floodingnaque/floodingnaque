/**
 * Resident — My Household Page
 */

import { Heart, Plus, Users } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useUser } from "@/state";

export default function ResidentHouseholdPage() {
  const user = useUser();
  const [editing, setEditing] = useState(false);

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto pb-24 md:pb-6">
      {/* Household Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Heart className="h-4 w-4 text-red-500" />
            My Household
          </CardTitle>
          <CardDescription>
            Register household members for emergency tracking and assistance
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Head of Household</p>
              <Input defaultValue={user?.name ?? ""} readOnly={!editing} />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Barangay</p>
              <Input placeholder="Your barangay" readOnly={!editing} />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Address</p>
              <Input
                placeholder="House/Block/Lot, Street"
                readOnly={!editing}
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Contact Number</p>
              <Input placeholder="09XX-XXX-XXXX" readOnly={!editing} />
            </div>
          </div>
          <Button
            variant={editing ? "default" : "outline"}
            size="sm"
            onClick={() => setEditing(!editing)}
          >
            {editing ? "Save" : "Edit"}
          </Button>
        </CardContent>
      </Card>

      {/* Household Members */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Users className="h-4 w-4 text-primary" />
              Household Members
            </CardTitle>
            <Button variant="outline" size="sm" className="gap-2">
              <Plus className="h-4 w-4" />
              Add Member
            </Button>
          </div>
          <CardDescription>
            Register family members, especially elderly, children, and PWDs
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Users className="h-10 w-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">No members registered</p>
            <p className="text-xs mt-1">
              Add household members for emergency tracking
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Vulnerability */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Vulnerability Information</CardTitle>
          <CardDescription>
            This helps MDRRMO prioritize assistance during evacuations
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>Does your household include any of the following?</p>
          <div className="grid grid-cols-2 gap-2">
            {[
              "Senior citizen (60+)",
              "Children under 5",
              "Pregnant woman",
              "Person with disability",
              "Bedridden member",
              "Solo parent",
            ].map((item) => (
              <div
                key={item}
                className="flex items-center gap-2 p-2 rounded-lg border border-border/50 hover:bg-accent/50 cursor-pointer transition-colors"
              >
                <div className="h-4 w-4 rounded border border-border" />
                <span className="text-xs">{item}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
