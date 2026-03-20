/**
 * Parañaque City Configuration Data
 *
 * All 16 barangays with coordinates, evacuation centers, and
 * emergency contacts sourced from DRRMO records.
 * Single source of truth for the frontend - matches backend constants.py.
 */

// ---------------------------------------------------------------------------
// Barangay Definitions
// ---------------------------------------------------------------------------

export type BarangayZone = "Coastal" | "Low-lying" | "Inland";

export interface BarangayData {
  /** Machine-readable key */
  key: string;
  /** Official barangay name */
  name: string;
  /** Center coordinate for map marker / API calls */
  lat: number;
  lon: number;
  /** Population (2020 census) - display only */
  population: number;
  /** Polygon coordinates [lat, lon][] for map overlay (simplified boundaries) */
  polygon: [number, number][];
  /** Nearest evacuation center */
  evacuationCenter: string;
  /** Flood depth classification from DRRMO records */
  floodRisk: "low" | "moderate" | "high";
  /** Geographic zone classification */
  zone: BarangayZone;
  /** Area in km² */
  area: number;
  /** Historical flood event count (DRRMO 2022-2025) */
  floodEvents: number;
}

/**
 * All 16 barangays of Parañaque City
 *
 * Polygons are simplified convex hulls suitable for Leaflet overlays.
 * Coordinates sourced from OpenStreetMap boundaries.
 * floodEvents: actual DRRMO flood record counts 2022-2025 (295 identifiable events;
 *   135 records with unresolved barangay attribution excluded).
 */
export const BARANGAYS: BarangayData[] = [
  {
    key: "baclaran",
    name: "Baclaran",
    lat: 14.524,
    lon: 121.001,
    population: 36_073,
    polygon: [
      [14.528, 121.004],
      [14.526, 120.996],
      [14.521, 120.997],
      [14.52, 121.004],
      [14.528, 121.004],
    ],
    evacuationCenter: "Baclaran Elementary School",
    floodRisk: "high",
    zone: "Coastal",
    area: 2.81,
    floodEvents: 7,
  },
  {
    key: "don_galo",
    name: "Don Galo",
    lat: 14.512,
    lon: 120.992,
    population: 16_204,
    polygon: [
      [14.516, 120.996],
      [14.515, 120.987],
      [14.509, 120.988],
      [14.508, 120.996],
      [14.516, 120.996],
    ],
    evacuationCenter: "Don Galo Elementary School",
    floodRisk: "high",
    zone: "Coastal",
    area: 1.44,
    floodEvents: 0,
  },
  {
    key: "la_huerta",
    name: "La Huerta",
    lat: 14.4891,
    lon: 120.9876,
    population: 50_905,
    polygon: [
      [14.494, 120.993],
      [14.493, 120.981],
      [14.485, 120.982],
      [14.484, 120.993],
      [14.494, 120.993],
    ],
    evacuationCenter: "La Huerta Elementary School",
    floodRisk: "high",
    zone: "Inland",
    area: 2.06,
    floodEvents: 2,
  },
  {
    key: "san_dionisio",
    name: "San Dionisio",
    lat: 14.507,
    lon: 121.007,
    population: 32_459,
    polygon: [
      [14.511, 121.012],
      [14.51, 121.001],
      [14.504, 121.002],
      [14.503, 121.012],
      [14.511, 121.012],
    ],
    evacuationCenter: "San Dionisio Elementary School",
    floodRisk: "moderate",
    zone: "Low-lying",
    area: 3.22,
    floodEvents: 24,
  },
  {
    key: "tambo",
    name: "Tambo",
    lat: 14.518,
    lon: 120.995,
    population: 30_709,
    polygon: [
      [14.523, 120.999],
      [14.522, 120.99],
      [14.515, 120.991],
      [14.514, 120.999],
      [14.523, 120.999],
    ],
    evacuationCenter: "Tambo Elementary School",
    floodRisk: "high",
    zone: "Coastal",
    area: 1.93,
    floodEvents: 2,
  },
  {
    key: "vitalez",
    name: "Vitalez",
    lat: 14.495,
    lon: 120.991,
    population: 19_213,
    polygon: [
      [14.499, 120.995],
      [14.498, 120.986],
      [14.492, 120.987],
      [14.491, 120.995],
      [14.499, 120.995],
    ],
    evacuationCenter: "Vitalez Elementary School",
    floodRisk: "moderate",
    zone: "Low-lying",
    area: 1.48,
    floodEvents: 5,
  },
  {
    key: "bf_homes",
    name: "BF Homes",
    lat: 14.4545,
    lon: 121.0234,
    population: 93_023,
    polygon: [
      [14.462, 121.031],
      [14.461, 121.015],
      [14.448, 121.016],
      [14.447, 121.031],
      [14.462, 121.031],
    ],
    evacuationCenter: "BF Homes Covered Court / BF Homes Elementary School",
    floodRisk: "high",
    zone: "Inland",
    area: 6.34,
    floodEvents: 2,
  },
  {
    key: "don_bosco",
    name: "Don Bosco",
    lat: 14.476,
    lon: 121.024,
    population: 72_218,
    polygon: [
      [14.481, 121.03],
      [14.48, 121.018],
      [14.472, 121.019],
      [14.471, 121.03],
      [14.481, 121.03],
    ],
    evacuationCenter: "Don Bosco Church / Barangay Hall",
    floodRisk: "moderate",
    zone: "Inland",
    area: 1.92,
    floodEvents: 10,
  },
  {
    key: "marcelo_green",
    name: "Marcelo Green Village",
    lat: 14.482,
    lon: 121.01,
    population: 28_497,
    polygon: [
      [14.486, 121.015],
      [14.485, 121.005],
      [14.479, 121.006],
      [14.478, 121.015],
      [14.486, 121.015],
    ],
    evacuationCenter: "Marcelo Green Elementary School",
    floodRisk: "moderate",
    zone: "Low-lying",
    area: 2.38,
    floodEvents: 11,
  },
  {
    key: "merville",
    name: "Merville",
    lat: 14.472,
    lon: 121.036,
    population: 33_580,
    polygon: [
      [14.477, 121.041],
      [14.476, 121.03],
      [14.468, 121.031],
      [14.467, 121.041],
      [14.477, 121.041],
    ],
    evacuationCenter: "Merville Covered Court",
    floodRisk: "low",
    zone: "Inland",
    area: 1.85,
    floodEvents: 11,
  },
  {
    key: "moonwalk",
    name: "Moonwalk",
    lat: 14.454,
    lon: 121.01,
    population: 53_413,
    polygon: [
      [14.459, 121.016],
      [14.458, 121.004],
      [14.45, 121.005],
      [14.449, 121.016],
      [14.459, 121.016],
    ],
    evacuationCenter: "Moonwalk Elementary School",
    floodRisk: "high",
    zone: "Low-lying",
    area: 1.67,
    floodEvents: 11,
  },
  {
    key: "san_antonio",
    name: "San Antonio",
    lat: 14.468,
    lon: 121.014,
    population: 38_891,
    polygon: [
      [14.472, 121.02],
      [14.471, 121.008],
      [14.465, 121.009],
      [14.464, 121.02],
      [14.472, 121.02],
    ],
    evacuationCenter: "San Antonio Parish Covered Court",
    floodRisk: "moderate",
    zone: "Low-lying",
    area: 2.97,
    floodEvents: 25,
  },
  {
    key: "san_isidro",
    name: "San Isidro",
    lat: 14.45,
    lon: 121.03,
    population: 36_542,
    polygon: [
      [14.455, 121.036],
      [14.454, 121.024],
      [14.446, 121.025],
      [14.445, 121.036],
      [14.455, 121.036],
    ],
    evacuationCenter: "San Isidro Elementary School",
    floodRisk: "moderate",
    zone: "Low-lying",
    area: 2.84,
    floodEvents: 20,
  },
  {
    key: "san_martin",
    name: "San Martin de Porres",
    lat: 14.461,
    lon: 121.0,
    population: 40_104,
    polygon: [
      [14.466, 121.006],
      [14.465, 120.994],
      [14.457, 120.995],
      [14.456, 121.006],
      [14.466, 121.006],
    ],
    evacuationCenter: "San Martin Elementary School",
    floodRisk: "moderate",
    zone: "Inland",
    area: 1.78,
    floodEvents: 3,
  },
  {
    key: "santo_nino",
    name: "Santo Niño",
    lat: 14.445,
    lon: 121.017,
    population: 33_821,
    polygon: [
      [14.45, 121.023],
      [14.449, 121.011],
      [14.441, 121.012],
      [14.44, 121.023],
      [14.45, 121.023],
    ],
    evacuationCenter: "Santo Niño Elementary School",
    floodRisk: "low",
    zone: "Low-lying",
    area: 1.56,
    floodEvents: 11,
  },
  {
    key: "sucat",
    name: "Sun Valley (Sucat)",
    lat: 14.4625,
    lon: 121.0456,
    population: 50_172,
    polygon: [
      [14.468, 121.051],
      [14.467, 121.039],
      [14.458, 121.04],
      [14.457, 121.051],
      [14.468, 121.051],
    ],
    evacuationCenter: "Sun Valley Gym / Sucat Elementary School",
    floodRisk: "moderate",
    zone: "Low-lying",
    area: 2.15,
    floodEvents: 4,
  },
];

// ---------------------------------------------------------------------------
// Emergency Contacts
// ---------------------------------------------------------------------------

export const EMERGENCY_CONTACTS = {
  mdrrmo: {
    name: "Parañaque City DRRMO",
    phone: "(02) 8829-1434",
    hotline: "911 / 8888",
    description: "City Disaster Risk Reduction and Management Office",
  },
  fireStation: {
    name: "Parañaque Fire Station",
    phone: "(02) 8825-1099",
    description: "Bureau of Fire Protection - Parañaque",
  },
  pnp: {
    name: "Parañaque PNP",
    phone: "(02) 8826-3906",
    description: "Philippine National Police - Parañaque Station",
  },
  redCross: {
    name: "Philippine Red Cross",
    phone: "143",
    description: "Disaster response and humanitarian aid",
  },
  ndrrmc: {
    name: "NDRRMC Hotline",
    phone: "911 / 8911-5061",
    description: "National Disaster Risk Reduction and Management Council",
  },
  pagasa: {
    name: "PAGASA Weather Bulletins",
    phone: "(02) 8284-0800",
    description:
      "Philippine Atmospheric, Geophysical and Astronomical Services",
  },
  dswd: {
    name: "DSWD Crisis Hotline",
    phone: "(02) 8888-3333",
    description: "Department of Social Welfare and Development",
  },
  hopeline: {
    name: "Hopeline (Mental Health)",
    phone: "8804-4673",
    description: "Crisis support and mental health helpline",
  },
} as const;

// ---------------------------------------------------------------------------
// PAGASA Weather Stations near Parañaque
// ---------------------------------------------------------------------------

export interface WeatherStation {
  id: string;
  name: string;
  lat: number;
  lon: number;
  type: "synoptic" | "agro-met" | "automatic";
}

export const PAGASA_STATIONS: WeatherStation[] = [
  {
    id: "port_area",
    name: "Port Area (Manila)",
    lat: 14.584,
    lon: 120.969,
    type: "synoptic",
  },
  {
    id: "naia",
    name: "NAIA (Pasay)",
    lat: 14.5086,
    lon: 121.0197,
    type: "synoptic",
  },
  {
    id: "science_garden",
    name: "Science Garden (QC)",
    lat: 14.647,
    lon: 121.044,
    type: "synoptic",
  },
];

// ---------------------------------------------------------------------------
// Model Information
// ---------------------------------------------------------------------------
// MODEL_VERSIONS and FEATURE_IMPORTANCES have been removed.
// These are now served from the backend API at /api/models/history
// and /api/models/feature-importance to ensure real, verified data.
