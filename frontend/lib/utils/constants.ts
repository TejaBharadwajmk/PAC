/**
 * PAC — Karnataka Districts & Domain Constants
 * Single source of truth for all fixed enumerations used across the UI.
 */

export const KARNATAKA_DISTRICTS = [
  "Bagalkot", "Ballari", "Belagavi", "Bengaluru Rural", "Bengaluru Urban",
  "Bidar", "Chamarajanagar", "Chikkaballapur", "Chikkamagaluru", "Chitradurga",
  "Dakshina Kannada", "Davanagere", "Dharwad", "Gadag", "Hassan",
  "Haveri", "Kalaburagi", "Kodagu", "Kolar", "Koppal",
  "Mandya", "Mysuru", "Raichur", "Ramanagara", "Shivamogga",
  "Tumakuru", "Udupi", "Uttara Kannada", "Vijayapura", "Yadgir",
] as const;

export type KarnatakaDistrict = typeof KARNATAKA_DISTRICTS[number];

export const CRIME_TYPE_LABELS: Record<string, string> = {
  murder:          "Murder",
  robbery:         "Robbery",
  burglary:        "Burglary",
  theft:           "Theft",
  chain_snatching: "Chain Snatching",
  vehicle_theft:   "Vehicle Theft",
  house_break_in:  "House Break-In",
  auto_theft:      "Auto Theft",
  cyber_crime:     "Cyber Crime",
  atm_fraud:       "ATM Fraud",
  assault:         "Assault",
  kidnapping:      "Kidnapping",
  fraud:           "Fraud",
  dacoity:         "Dacoity",
  extortion:       "Extortion",
  drug_offense:    "Drug Offense",
  sexual_assault:  "Sexual Assault",
  other:           "Other",
};

export const CRIME_STATUS_LABELS: Record<string, string> = {
  registered:           "Registered",
  under_investigation:  "Under Investigation",
  chargesheeted:        "Chargesheeted",
  solved:               "Solved",
  closed:               "Closed",
};

export const CRIME_SEVERITY_LABELS: Record<string, string> = {
  low:      "Low",
  medium:   "Medium",
  high:     "High",
  critical: "Critical",
};

export const USER_ROLE_LABELS: Record<string, string> = {
  officer:    "Officer",
  analyst:    "Analyst",
  supervisor: "Supervisor",
  admin:      "Administrator",
};

export const REPORT_TYPE_LABELS: Record<string, string> = {
  fir_investigation:    "FIR Investigation",
  criminal_intelligence:"Criminal Intelligence",
  district_crime:       "District Crime Analysis",
  hotspot_assessment:   "Hotspot Assessment",
  gang_intelligence:    "Gang Intelligence",
};

// PAC Intelligence module source labels (from backend)
export const INTEL_SOURCE_LABELS: Record<string, string> = {
  "Crime DNA":                          "Crime DNA",
  "Hybrid Similarity Engine":           "Similarity",
  "Behaviour Intelligence":             "Behaviour",
  "Predictive Intelligence":            "Prediction",
  "Criminal Network Intelligence (Neo4j)": "Network",
  "Geo Intelligence":                   "Geo Intel",
};

// Map center: Karnataka, India
export const KARNATAKA_MAP_CENTER: [number, number] = [76.5, 15.0];
export const KARNATAKA_MAP_ZOOM = 7;

// Backend API base (empty string uses same-origin Next.js rewrites in browser)
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

// Internal backend URL for Next.js BFF server-side route handlers
export const BACKEND_URL = process.env.INTERNAL_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";


// DNA polling interval in ms
export const DNA_POLL_INTERVAL_MS = 10_000;

// TanStack Query stale times
export const STALE_TIME = {
  crimes:         30_000,
  criminals:      60_000,
  crimeDetail:    60_000,
  criminalDetail: 300_000,
  hotspots:       600_000,
  behaviour:      900_000,
  graph:          300_000,
  predictions:    600_000,
  assistant:      0,
} as const;
