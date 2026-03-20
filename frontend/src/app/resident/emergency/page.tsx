/**
 * Resident — Emergency Contacts Page
 */

import { ExternalLink, Phone } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface Contact {
  name: string;
  number: string;
  description: string;
}

const CONTACTS: Contact[] = [
  {
    name: "Parañaque MDRRMO",
    number: "(02) 8825-0907",
    description: "Municipal Disaster Risk Reduction & Management Office",
  },
  {
    name: "National Emergency Hotline",
    number: "911",
    description: "Philippine National Emergency Number",
  },
  {
    name: "NDRRMC Operations Center",
    number: "(02) 8911-5061",
    description: "National Disaster Risk Reduction & Management Council",
  },
  {
    name: "Philippine Red Cross",
    number: "143",
    description: "Red Cross emergency hotline",
  },
  {
    name: "PNP Emergency Hotline",
    number: "117",
    description: "Philippine National Police",
  },
  {
    name: "Bureau of Fire Protection",
    number: "(02) 8426-0219",
    description: "Fire and rescue services",
  },
];

export default function ResidentEmergencyPage() {
  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto pb-24 md:pb-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Phone className="h-4 w-4 text-red-500" />
            Emergency Contacts
          </CardTitle>
          <CardDescription>
            Tap a number to call directly. Save these numbers in your phone.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {CONTACTS.map((c) => (
            <a
              key={c.number}
              href={`tel:${c.number.replace(/[^0-9+]/g, "")}`}
              className="flex items-center gap-4 p-4 rounded-lg border border-border/50 hover:bg-accent/50 transition-colors"
            >
              <div className="h-10 w-10 rounded-full bg-red-500/10 flex items-center justify-center shrink-0">
                <Phone className="h-5 w-5 text-red-500" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{c.name}</p>
                <p className="text-xs text-muted-foreground">{c.description}</p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-sm font-mono font-medium text-primary">
                  {c.number}
                </p>
                <ExternalLink className="h-3 w-3 text-muted-foreground ml-auto mt-0.5" />
              </div>
            </a>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
