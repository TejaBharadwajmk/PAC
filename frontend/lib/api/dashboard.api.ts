import { pacClient } from "@/lib/api/pacClient";

export interface DashboardSummaryItem {
  id: string;
  fir_number: string;
  crime_type: string;
  severity: string;
  status: string;
  district: string;
  police_station: string;
  occurred_at: string;
}

export interface DashboardSummary {
  total_crimes: number;
  open_cases: number;
  solved_cases: number;
  high_severity_cases: number;
  hotspots_count: number;
  graph_nodes_count: number;
  graph_edges_count: number;
  recent_crimes: DashboardSummaryItem[];
  system_status: Record<string, string>;
  cached_at?: string;
}

export const dashboardApi = {
  /** Fetch consolidated, Redis-cached dashboard summary. */
  getSummary: async (): Promise<DashboardSummary> => {
    const res = await pacClient.get<DashboardSummary>("/api/v1/dashboard/summary");
    return res.data;
  },
};
