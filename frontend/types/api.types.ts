/**
 * PAC — Complete API Type System
 * Mirrors all FastAPI/Pydantic schemas exactly.
 * Single source of truth for all frontend API types.
 */

// ── Enums (mirrors backend Python enums) ─────────────────────────────────────

export type UserRole = "officer" | "analyst" | "supervisor" | "admin";

export type CrimeType =
  | "murder"
  | "robbery"
  | "burglary"
  | "theft"
  | "chain_snatching"
  | "vehicle_theft"
  | "house_break_in"
  | "auto_theft"
  | "cyber_crime"
  | "atm_fraud"
  | "assault"
  | "kidnapping"
  | "fraud"
  | "dacoity"
  | "extortion"
  | "drug_offense"
  | "sexual_assault"
  | "other";

export type CrimeStatus =
  | "registered"
  | "under_investigation"
  | "chargesheeted"
  | "solved"
  | "closed";

export type CrimeSeverity = "low" | "medium" | "high" | "critical";

export type RiskLevel = "LOW" | "MODERATE" | "HIGH" | "CRITICAL";

export type DnaStatus = "pending" | "processing" | "completed" | "failed";

export type EntityType = "criminal" | "district" | "hotspot" | "gang" | "investigation";

export type ReportType =
  | "fir_investigation"
  | "criminal_intelligence"
  | "district_crime"
  | "hotspot_assessment"
  | "gang_intelligence";

// ── Common Shapes ─────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items:     T[];
  total:     number;
  page:      number;
  page_size: number;
  has_next:  boolean;
  has_prev:  boolean;
}

export interface MessageResponse {
  message: string;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface LoginRequest {
  badge_number: string;
  password:     string;
}

export interface TokenResponse {
  access_token:  string;
  refresh_token: string;
  token_type:    string;
  expires_in:    number;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface UserResponse {
  id:             string;
  badge_number:   string;
  full_name:      string;
  email:          string;
  district:       string | null;
  police_station: string | null;
  role:           UserRole;
  is_active:      boolean;
}

export interface UserCreate {
  badge_number:   string;
  full_name:      string;
  email:          string;
  password:       string;
  district?:      string;
  police_station?: string;
  role:           UserRole;
}

export interface UserUpdate {
  full_name?:      string;
  email?:          string;
  district?:       string;
  police_station?: string;
  is_active?:      boolean;
}

// ── Crime MO ──────────────────────────────────────────────────────────────────

export interface CrimeMOResponse {
  id:                   string;
  crime_id:             string;
  crime_method:         string | null;
  entry_method:         string | null;
  target_type:          string | null;
  weapon_used:          string | null;
  tools_used:           string[];
  time_of_day:          string | null;
  day_type:             string | null;
  planning_level:       string | null;
  gang_involved:        boolean;
  num_accused:          number;
  escape_method:        string | null;
  vehicle_used_in_crime: boolean;
  modus_operandi_tags:  string[];
  extraction_method:    string;
  extracted_at:         string;
}

export interface CrimeMOCreate {
  crime_method?:         string;
  entry_method?:         string;
  target_type?:          string;
  weapon_used?:          string;
  tools_used?:           string[];
  time_of_day?:          string;
  day_type?:             string;
  planning_level?:       string;
  gang_involved?:        boolean;
  num_accused?:          number;
  escape_method?:        string;
  vehicle_used_in_crime?: boolean;
  modus_operandi_tags?:  string[];
}

// ── Crimes ────────────────────────────────────────────────────────────────────

export interface CrimeCreate {
  fir_number:       string;
  crime_type:       CrimeType;
  severity:         CrimeSeverity;
  district:         string;
  police_station:   string;
  location_address?: string;
  latitude?:        number;
  longitude?:       number;
  description?:     string;
  mo_text?:         string;
  occurred_at:      string; // ISO 8601
  mo_features?:     CrimeMOCreate;
}

export interface CrimeUpdate {
  crime_type?:      CrimeType;
  severity?:        CrimeSeverity;
  status?:          CrimeStatus;
  district?:        string;
  police_station?:  string;
  location_address?: string;
  latitude?:        number;
  longitude?:       number;
  description?:     string;
  mo_text?:         string;
  occurred_at?:     string;
}

export interface CrimeResponse {
  id:               string;
  fir_number:       string;
  crime_type:       CrimeType;
  severity:         CrimeSeverity;
  status:           CrimeStatus;
  district:         string;
  police_station:   string;
  location_address: string | null;
  latitude:         number | null;
  longitude:        number | null;
  description:      string | null;
  mo_text:          string | null;
  occurred_at:      string;
  reported_at:      string | null;
  registered_by:    string | null;
  has_dna?:         boolean;
  created_at:       string;

  updated_at:       string;
  mo_features:      CrimeMOResponse | null;
}

export interface CrimeListItem {
  id:             string;
  fir_number:     string;
  crime_type:     CrimeType;
  severity:       CrimeSeverity;
  status:         CrimeStatus;
  district:       string;
  police_station: string;
  occurred_at:    string;
  latitude:       number | null;
  longitude:      number | null;
}

// ── Criminals ─────────────────────────────────────────────────────────────────

export interface CriminalResponse {
  id:                   string;
  name:                 string;
  aliases:              string[];
  date_of_birth:        string | null;
  age:                  number | null;
  gender:               string;
  district:             string | null;
  state:                string;
  address:              string | null;
  is_repeat_offender:   boolean;
  previous_cases_count: number;
  gang_name:            string | null;
  gang_affiliation:     boolean;
  is_wanted:            boolean;
  is_arrested:          boolean;
  created_at:           string;
}

export interface CriminalListItem {
  id:                   string;
  name:                 string;
  aliases:              string[];
  district:             string | null;
  is_repeat_offender:   boolean;
  gang_name:            string | null;
  is_wanted:            boolean;
  previous_cases_count: number;
}

// ── Similarity ────────────────────────────────────────────────────────────────

export interface SimilarityMatch {
  crime_id:        string;
  fir_number:      string;
  crime_type:      CrimeType;
  district:        string;
  occurred_at:     string;
  similarity_score: number;
  mo_text:         string | null;
}

export interface SimilaritySearchRequest {
  query_text:        string;
  limit?:             number;
  min_similarity?:    number;
  district?:          string;
  crime_type?:        CrimeType;
}

export interface SimilaritySearchResponse {
  query_text: string;
  results:    SimilarityMatch[];
  total_candidates_scanned?: number;
}


// ── Geo Intelligence ──────────────────────────────────────────────────────────

export interface HotspotResponse {
  cluster_id:              number;
  center_latitude:         number;
  center_longitude:        number;
  radius_meters:           number;
  crime_count:             number;
  dominant_crime_type:     CrimeType | string;
  peak_time?:              string;
  suggested_patrol_window?: string;
  hotspot_trend?:          string;
  confidence_score?:       number;
  risk_level?:             string;
  repeat_offenders_count?: number;
  known_gangs_count?:      number;
  recommendation?:         string;
}

export interface GeoStatisticsResponse {
  total_crimes_analyzed:        number;
  total_hotspots_detected:      number;
  total_clustered_crimes:       number;
  total_noise_crimes:           number;
  top_hotspot_district:         string | null;
  average_hotspot_radius_meters: number;
  highest_risk_hotspot_id:      number | null;
}


// ── Network Intelligence ──────────────────────────────────────────────────────

export interface GraphNode {
  id:         string;
  label:      string;
  type:       "criminal" | "crime" | "gang" | "victim" | "district";
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source:             string;
  target:             string;
  relationship:       string;
  association_strength?: number;
  properties:         Record<string, unknown>;
}

export interface NetworkGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  statistics: {
    node_count: number;
    edge_count: number;
    density:    number;
  };
}

export interface GraphStatisticsResponse {
  total_nodes:    number;
  total_edges:    number;
  criminal_nodes: number;
  crime_nodes:    number;
  gang_nodes:     number;
  density:        number;
}

// ── Behaviour Intelligence ────────────────────────────────────────────────────

export interface BehaviourProfileResponse {
  criminal_id:           string;
  preferred_crime_types: CrimeType[];
  preferred_time:        string | null;
  preferred_district:    string | null;
  preferred_method:      string | null;
  violence_index:        number;
  recidivism_count:      number;
  operating_radius_km:   number;
  gang_associations:     string[];
  consistency_score:     number;
  escalation_pattern:    string | null;
  last_active:           string | null;
  total_crimes:          number;
}

export interface BehaviourStatisticsResponse {
  total_profiles:            number;
  average_violence_index:    number;
  average_recidivism:        number;
  high_recidivism_count:     number;
  gang_affiliated_count:     number;
}

// ── Predictions ───────────────────────────────────────────────────────────────

export interface PredictionScoreBreakdown {
  crime_severity:         number;
  recency:                number;
  repeat_offending:       number;
  behaviour_consistency:  number;
  violence:               number;
  gang_influence:         number;
  network_influence:      number;
  hotspot_exposure:       number;
  escalation:             number;
}

export interface PredictionResponse {
  id:                   string;
  entity_type:          EntityType;
  entity_id:            string;
  prediction_type:      string;
  prediction_score:     number;
  confidence:           number;
  risk_level:           RiskLevel | null;
  prediction_reason_code: string | null;
  prediction_version:   string;
  generated_at:         string;
  evidence:             string[];
  recommendations:      string[];
  score_breakdown:      Record<string, number>;
  detailed_metrics:     Record<string, unknown>;
}

export interface DistrictRiskResponse {
  district:        string;
  risk_score:      number;
  risk_level:      RiskLevel;
  confidence:      number;
  evidence:        string[];
  recommendations: string[];
  hotspot_count:   number;
  crime_volume:    number;
}

export interface GangThreatResponse {
  gang_name:       string;
  threat_level:    RiskLevel;
  threat_score:    number;
  confidence:      number;
  evidence:        string[];
  recommendations: string[];
  member_count:    number;
  crime_count:     number;
}

export interface HotspotForecastResponse {
  district:        string;
  growth_trend:    string;
  score:           number;
  confidence:      number;
  evidence:        string[];
  recommendations: string[];
}

export interface PredictionStatisticsResponse {
  total_criminal_predictions:  number;
  average_criminal_risk_score: number;
  risk_level_distribution:     Record<string, number>;
}

// ── AI Assistant ──────────────────────────────────────────────────────────────

export interface AssistantChatRequest {
  question:    string;
  session_id?: string;
  criminal_id?: string;
  crime_id?:   string;
  district?:   string;
  gang_name?:  string;
}

export interface AssistantChatResponse {
  answer:              string;
  confidence:          number;
  intent:              string;
  sources:             string[];
  evidence:            string[];
  recommendations:     string[];
  follow_up_questions: string[];
  session_id:          string;
  is_grounded:         boolean;
  latency_ms:          number;
}

export interface ReportRequest {
  report_type:  ReportType;
  crime_id?:    string;
  criminal_id?: string;
  district?:    string;
  gang_name?:   string;
}

export interface ReportResponse {
  title:              string;
  executive_summary:  string;
  key_findings:       string[];
  evidence:           string[];
  risk_assessment:    Record<string, unknown>;
  recommendations:    string[];
  suggested_next_actions: string[];
  metadata:           Record<string, unknown>;
}

export interface AssistantHealthResponse {
  provider:           string;
  model:              string | null;
  status:             string;
  available_modules:  string[];
  supported_intents:  string[];
}

// ── Chat Message (frontend-only) ──────────────────────────────────────────────

export interface ChatMessage {
  id:        string;
  role:      "user" | "assistant";
  content:   string;
  timestamp: string;
  response?: AssistantChatResponse;
}

// ── Assistant Context (frontend-only) ─────────────────────────────────────────

export interface AssistantContext {
  criminal_id?: string;
  crime_id?:    string;
  district?:    string;
  gang_name?:   string;
}
