/**
 * Parañaque City Barangay Data
 *
 * Reference data for all 16 barangays including zone classification,
 * flood risk levels, and nearest evacuation centers.
 * Used in the registration form for auto-populating location fields.
 */

export interface BarangayInfo {
  name: string;
  zoneType: "Coastal" | "Inland" | "Low-lying";
  floodRisk: "High" | "Moderate" | "Low";
  evacuationCenter: string;
}

export const PARANAQUE_BARANGAYS: BarangayInfo[] = [
  {
    name: "Baclaran",
    zoneType: "Coastal",
    floodRisk: "High",
    evacuationCenter: "Baclaran Covered Court",
  },
  {
    name: "BF Homes",
    zoneType: "Inland",
    floodRisk: "Low",
    evacuationCenter: "BF Homes Barangay Hall",
  },
  {
    name: "Don Bosco",
    zoneType: "Coastal",
    floodRisk: "High",
    evacuationCenter: "Don Bosco Barangay Hall",
  },
  {
    name: "Don Galo",
    zoneType: "Coastal",
    floodRisk: "High",
    evacuationCenter: "Don Galo Elementary School",
  },
  {
    name: "La Huerta",
    zoneType: "Coastal",
    floodRisk: "High",
    evacuationCenter: "La Huerta Covered Court",
  },
  {
    name: "Marcelo Green Village",
    zoneType: "Inland",
    floodRisk: "Moderate",
    evacuationCenter: "Marcelo Green Village Barangay Hall",
  },
  {
    name: "Merville",
    zoneType: "Inland",
    floodRisk: "Moderate",
    evacuationCenter: "Merville Barangay Hall",
  },
  {
    name: "Moonwalk",
    zoneType: "Low-lying",
    floodRisk: "High",
    evacuationCenter: "Moonwalk Elementary School",
  },
  {
    name: "San Antonio",
    zoneType: "Inland",
    floodRisk: "Low",
    evacuationCenter: "San Antonio Barangay Hall",
  },
  {
    name: "San Dionisio",
    zoneType: "Low-lying",
    floodRisk: "Moderate",
    evacuationCenter: "San Dionisio Covered Court",
  },
  {
    name: "San Isidro",
    zoneType: "Low-lying",
    floodRisk: "High",
    evacuationCenter: "San Isidro Elementary School",
  },
  {
    name: "San Martin de Porres",
    zoneType: "Inland",
    floodRisk: "Low",
    evacuationCenter: "San Martin de Porres Barangay Hall",
  },
  {
    name: "Santo Niño",
    zoneType: "Low-lying",
    floodRisk: "Moderate",
    evacuationCenter: "Santo Niño Covered Court",
  },
  {
    name: "Sun Valley",
    zoneType: "Inland",
    floodRisk: "Moderate",
    evacuationCenter: "Sun Valley Barangay Hall",
  },
  {
    name: "Tambo",
    zoneType: "Coastal",
    floodRisk: "High",
    evacuationCenter: "Tambo Elementary School",
  },
  {
    name: "Vitalez",
    zoneType: "Low-lying",
    floodRisk: "Moderate",
    evacuationCenter: "Vitalez Barangay Hall",
  },
];

export const BARANGAY_NAMES = PARANAQUE_BARANGAYS.map((b) => b.name);

export function getBarangayInfo(name: string): BarangayInfo | undefined {
  return PARANAQUE_BARANGAYS.find((b) => b.name === name);
}

export const CIVIL_STATUS_OPTIONS = [
  "Single",
  "Married",
  "Widowed",
  "Separated",
] as const;
export const SEX_OPTIONS = ["Male", "Female", "Prefer not to say"] as const;
export const HOME_TYPE_OPTIONS = [
  "Concrete",
  "Semi-Concrete",
  "Wood",
  "Makeshift",
] as const;
export const FLOOR_LEVEL_OPTIONS = [
  "Ground Floor",
  "2nd Floor",
  "3rd Floor or higher",
] as const;
export const ALERT_LANGUAGE_OPTIONS = ["Filipino", "English"] as const;
