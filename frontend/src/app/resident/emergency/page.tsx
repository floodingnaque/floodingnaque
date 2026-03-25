/**
 * Resident — Emergency Contacts Page
 *
 * All 8 key contacts with one-tap call, "Save All to Contacts" vCard export.
 */

import { Download, ExternalLink, Phone } from "lucide-react";

import { Button } from "@/components/ui/button";
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
    name: "Parañaque DRRMO",
    number: "(02) 8825-0907",
    description: "Disaster Risk Reduction & Management Office",
  },
  {
    name: "National Emergency",
    number: "911",
    description: "Philippine National Emergency Hotline",
  },
  {
    name: "Bureau of Fire Protection",
    number: "(02) 8426-0219",
    description: "Fire station and rescue services",
  },
  {
    name: "PNP Emergency",
    number: "117",
    description: "Philippine National Police",
  },
  {
    name: "Philippine Red Cross",
    number: "143",
    description: "Emergency humanitarian assistance",
  },
  {
    name: "NDRRMC Operations",
    number: "(02) 8911-5061",
    description: "National Disaster Risk Reduction & Management Council",
  },
  {
    name: "PAGASA",
    number: "(02) 8927-1541",
    description: "Weather forecasts and typhoon bulletins",
  },
  {
    name: "DSWD Hotline",
    number: "(02) 8931-8101",
    description: "Dept. of Social Welfare & Development — relief assistance",
  },
];

function generateVCard(): string {
  return CONTACTS.map(
    (c) =>
      `BEGIN:VCARD\nVERSION:3.0\nFN:${c.name}\nTEL:${c.number}\nNOTE:${c.description}\nEND:VCARD`,
  ).join("\n");
}

function downloadVCard() {
  const blob = new Blob([generateVCard()], { type: "text/vcard" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "paranaque_emergency_contacts.vcf";
  a.click();
  URL.revokeObjectURL(url);
}

export default function ResidentEmergencyPage() {
  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      {/* ── Header ────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Phone className="h-4 w-4 text-red-500" />
                Mga Emergency Number / Emergency Contacts
              </CardTitle>
              <CardDescription>
                Tap a number to call directly. Save to your phone.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-2 self-start"
              onClick={downloadVCard}
            >
              <Download className="h-4 w-4" />
              Save All to Contacts
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {CONTACTS.map((c) => (
            <a
              key={c.number}
              href={`tel:${c.number.replace(/[^0-9+]/g, "")}`}
              className="flex items-center gap-4 p-4 rounded-xl border border-border/50 hover:bg-accent/50 transition-colors"
            >
              <div className="h-11 w-11 rounded-full bg-red-500/10 flex items-center justify-center shrink-0">
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
