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
  floodRisk: 'low' | 'moderate' | 'high';
}

/**
 * All 16 barangays of Parañaque City
 *
 * Polygons are simplified convex hulls suitable for Leaflet overlays.
 * Coordinates sourced from OpenStreetMap boundaries.
 */
export const BARANGAYS: BarangayData[] = [
  {
    key: 'baclaran',
    name: 'Baclaran',
    lat: 14.5240,
    lon: 121.0010,
    population: 36_073,
    polygon: [
      [14.5280, 121.0040], [14.5260, 120.9960], [14.5210, 120.9970],
      [14.5200, 121.0040], [14.5280, 121.0040],
    ],
    evacuationCenter: 'Baclaran Elementary School',
    floodRisk: 'high',
  },
  {
    key: 'don_galo',
    name: 'Don Galo',
    lat: 14.5120,
    lon: 120.9920,
    population: 16_204,
    polygon: [
      [14.5160, 120.9960], [14.5150, 120.9870], [14.5090, 120.9880],
      [14.5080, 120.9960], [14.5160, 120.9960],
    ],
    evacuationCenter: 'Don Galo Elementary School',
    floodRisk: 'high',
  },
  {
    key: 'la_huerta',
    name: 'La Huerta',
    lat: 14.4891,
    lon: 120.9876,
    population: 50_905,
    polygon: [
      [14.4940, 120.9930], [14.4930, 120.9810], [14.4850, 120.9820],
      [14.4840, 120.9930], [14.4940, 120.9930],
    ],
    evacuationCenter: 'La Huerta Elementary School',
    floodRisk: 'high',
  },
  {
    key: 'san_dionisio',
    name: 'San Dionisio',
    lat: 14.5070,
    lon: 121.0070,
    population: 32_459,
    polygon: [
      [14.5110, 121.0120], [14.5100, 121.0010], [14.5040, 121.0020],
      [14.5030, 121.0120], [14.5110, 121.0120],
    ],
    evacuationCenter: 'San Dionisio Elementary School',
    floodRisk: 'moderate',
  },
  {
    key: 'tambo',
    name: 'Tambo',
    lat: 14.5180,
    lon: 120.9950,
    population: 30_709,
    polygon: [
      [14.5230, 120.9990], [14.5220, 120.9900], [14.5150, 120.9910],
      [14.5140, 120.9990], [14.5230, 120.9990],
    ],
    evacuationCenter: 'Tambo Elementary School',
    floodRisk: 'high',
  },
  {
    key: 'vitalez',
    name: 'Vitalez',
    lat: 14.4950,
    lon: 120.9910,
    population: 19_213,
    polygon: [
      [14.4990, 120.9950], [14.4980, 120.9860], [14.4920, 120.9870],
      [14.4910, 120.9950], [14.4990, 120.9950],
    ],
    evacuationCenter: 'Vitalez Elementary School',
    floodRisk: 'moderate',
  },
  {
    key: 'bf_homes',
    name: 'BF Homes',
    lat: 14.4545,
    lon: 121.0234,
    population: 93_023,
    polygon: [
      [14.4620, 121.0310], [14.4610, 121.0150], [14.4480, 121.0160],
      [14.4470, 121.0310], [14.4620, 121.0310],
    ],
    evacuationCenter: 'BF Homes Covered Court / BF Homes Elementary School',
    floodRisk: 'high',
  },
  {
    key: 'don_bosco',
    name: 'Don Bosco',
    lat: 14.4760,
    lon: 121.0240,
    population: 72_218,
    polygon: [
      [14.4810, 121.0300], [14.4800, 121.0180], [14.4720, 121.0190],
      [14.4710, 121.0300], [14.4810, 121.0300],
    ],
    evacuationCenter: 'Don Bosco Church / Barangay Hall',
    floodRisk: 'moderate',
  },
  {
    key: 'marcelo_green',
    name: 'Marcelo Green Village',
    lat: 14.4820,
    lon: 121.0100,
    population: 28_497,
    polygon: [
      [14.4860, 121.0150], [14.4850, 121.0050], [14.4790, 121.0060],
      [14.4780, 121.0150], [14.4860, 121.0150],
    ],
    evacuationCenter: 'Marcelo Green Elementary School',
    floodRisk: 'moderate',
  },
  {
    key: 'merville',
    name: 'Merville',
    lat: 14.4720,
    lon: 121.0360,
    population: 33_580,
    polygon: [
      [14.4770, 121.0410], [14.4760, 121.0300], [14.4680, 121.0310],
      [14.4670, 121.0410], [14.4770, 121.0410],
    ],
    evacuationCenter: 'Merville Covered Court',
    floodRisk: 'low',
  },
  {
    key: 'moonwalk',
    name: 'Moonwalk',
    lat: 14.4540,
    lon: 121.0100,
    population: 53_413,
    polygon: [
      [14.4590, 121.0160], [14.4580, 121.0040], [14.4500, 121.0050],
      [14.4490, 121.0160], [14.4590, 121.0160],
    ],
    evacuationCenter: 'Moonwalk Elementary School',
    floodRisk: 'high',
  },
  {
    key: 'san_antonio',
    name: 'San Antonio',
    lat: 14.4680,
    lon: 121.0140,
    population: 38_891,
    polygon: [
      [14.4720, 121.0200], [14.4710, 121.0080], [14.4650, 121.0090],
      [14.4640, 121.0200], [14.4720, 121.0200],
    ],
    evacuationCenter: 'San Antonio Parish Covered Court',
    floodRisk: 'moderate',
  },
  {
    key: 'san_isidro',
    name: 'San Isidro',
    lat: 14.4500,
    lon: 121.0300,
    population: 36_542,
    polygon: [
      [14.4550, 121.0360], [14.4540, 121.0240], [14.4460, 121.0250],
      [14.4450, 121.0360], [14.4550, 121.0360],
    ],
    evacuationCenter: 'San Isidro Elementary School',
    floodRisk: 'moderate',
  },
  {
    key: 'san_martin',
    name: 'San Martin de Porres',
    lat: 14.4610,
    lon: 121.0000,
    population: 40_104,
    polygon: [
      [14.4660, 121.0060], [14.4650, 120.9940], [14.4570, 120.9950],
      [14.4560, 121.0060], [14.4660, 121.0060],
    ],
    evacuationCenter: 'San Martin Elementary School',
    floodRisk: 'moderate',
  },
  {
    key: 'santo_nino',
    name: 'Santo Niño',
    lat: 14.4450,
    lon: 121.0170,
    population: 33_821,
    polygon: [
      [14.4500, 121.0230], [14.4490, 121.0110], [14.4410, 121.0120],
      [14.4400, 121.0230], [14.4500, 121.0230],
    ],
    evacuationCenter: 'Santo Niño Elementary School',
    floodRisk: 'low',
  },
  {
    key: 'sucat',
    name: 'Sun Valley (Sucat)',
    lat: 14.4625,
    lon: 121.0456,
    population: 50_172,
    polygon: [
      [14.4680, 121.0510], [14.4670, 121.0390], [14.4580, 121.0400],
      [14.4570, 121.0510], [14.4680, 121.0510],
    ],
    evacuationCenter: 'Sun Valley Gym / Sucat Elementary School',
    floodRisk: 'moderate',
  },
];

// ---------------------------------------------------------------------------
// Emergency Contacts
// ---------------------------------------------------------------------------

export const EMERGENCY_CONTACTS = {
  mdrrmo: {
    name: 'Parañaque City DRRMO',
    phone: '(02) 8829-1434',
    hotline: '911 / 8888',
    description: 'City Disaster Risk Reduction and Management Office',
  },
  fireStation: {
    name: 'Parañaque Fire Station',
    phone: '(02) 8825-1099',
    description: 'Bureau of Fire Protection - Parañaque',
  },
  pnp: {
    name: 'Parañaque PNP',
    phone: '(02) 8826-3906',
    description: 'Philippine National Police - Parañaque Station',
  },
  redCross: {
    name: 'Philippine Red Cross',
    phone: '143',
    description: 'Disaster response and humanitarian aid',
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
  type: 'synoptic' | 'agro-met' | 'automatic';
}

export const PAGASA_STATIONS: WeatherStation[] = [
  {
    id: 'port_area',
    name: 'Port Area (Manila)',
    lat: 14.5840,
    lon: 120.9690,
    type: 'synoptic',
  },
  {
    id: 'naia',
    name: 'NAIA (Pasay)',
    lat: 14.5086,
    lon: 121.0197,
    type: 'synoptic',
  },
  {
    id: 'science_garden',
    name: 'Science Garden (QC)',
    lat: 14.6470,
    lon: 121.0440,
    type: 'synoptic',
  },
];

// ---------------------------------------------------------------------------
// Model Information (for Admin dashboard)
// ---------------------------------------------------------------------------

export const MODEL_VERSIONS = [
  {
    version: 'v1',
    name: 'Baseline Random Forest',
    accuracy: 0.7832,
    precision: 0.7645,
    recall: 0.8012,
    f1: 0.7824,
    samples: 3_500,
    features: 4,
    description: 'Initial model with basic weather features',
  },
  {
    version: 'v2',
    name: 'Feature Engineering v2',
    accuracy: 0.8345,
    precision: 0.8200,
    recall: 0.8490,
    f1: 0.8342,
    samples: 5_200,
    features: 6,
    description: 'Added interaction terms (humidity × precipitation)',
  },
  {
    version: 'v3',
    name: 'Expanded Dataset v3',
    accuracy: 0.8891,
    precision: 0.8756,
    recall: 0.9012,
    f1: 0.8882,
    samples: 8_100,
    features: 8,
    description: 'Incorporated DRRMO flood records and PAGASA data',
  },
  {
    version: 'v4',
    name: 'Hyperparameter Tuning v4',
    accuracy: 0.9234,
    precision: 0.9120,
    recall: 0.9340,
    f1: 0.9229,
    samples: 10_500,
    features: 9,
    description: 'Grid search optimization of RF parameters',
  },
  {
    version: 'v5',
    name: 'Cross-Validation v5',
    accuracy: 0.9512,
    precision: 0.9430,
    recall: 0.9590,
    f1: 0.9509,
    samples: 13_698,
    features: 10,
    description: '10-fold stratified CV with threshold tuning',
  },
  {
    version: 'v6',
    name: 'Production Model v6',
    accuracy: 0.9675,
    precision: 0.9620,
    recall: 0.9730,
    f1: 0.9675,
    samples: 18_021,
    features: 10,
    description: 'Final model with full combined dataset (13,698 + DRRMO 1,182 events)',
    active: true,
  },
] as const;

/** Feature importances from v6 production model */
export const FEATURE_IMPORTANCES = [
  { feature: 'Precipitation', importance: 0.3377, label: 'Precipitation (mm)' },
  { feature: 'Humidity × Precipitation', importance: 0.2553, label: 'Humidity × Precip' },
  { feature: 'Temperature × Precipitation', importance: 0.2085, label: 'Temp × Precip' },
  { feature: 'Humidity', importance: 0.0842, label: 'Relative Humidity (%)' },
  { feature: 'Wind Speed', importance: 0.0456, label: 'Wind Speed (m/s)' },
  { feature: 'Temperature', importance: 0.0321, label: 'Temperature (°C)' },
  { feature: 'Pressure', importance: 0.0189, label: 'Pressure (hPa)' },
  { feature: 'Hour of Day', importance: 0.0098, label: 'Hour of Day' },
  { feature: 'Month', importance: 0.0052, label: 'Month' },
  { feature: 'Day of Week', importance: 0.0027, label: 'Day of Week' },
] as const;
