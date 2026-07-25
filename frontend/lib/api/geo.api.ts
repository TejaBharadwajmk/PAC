import { pacClient } from "@/lib/api/pacClient";
import type {
  HotspotResponse, GeoStatisticsResponse,
} from "@/types/api.types";
import type { CrimeType } from "@/types/api.types";

export interface GeoFilterParams {
  eps?:         number;
  min_samples?: number;
  district?:    string;
  crime_type?:  CrimeType;
  start_date?:  string;
  end_date?:    string;
}

export const geoApi = {
  /** Get all spatial hotspots via DBSCAN clustering. */
  hotspots: async (params?: GeoFilterParams): Promise<HotspotResponse[]> => {
    const res = await pacClient.get<HotspotResponse[]>("/api/v1/geo/hotspots", { params });
    return res.data;
  },

  /** Get hotspots filtered by district. */
  districtHotspots: async (district: string, params?: GeoFilterParams): Promise<HotspotResponse[]> => {
    const res = await pacClient.get<HotspotResponse[]>(`/api/v1/geo/district/${district}`, { params });
    return res.data;
  },

  /** Get hotspots filtered by crime type. */
  crimeTypeHotspots: async (crimeType: CrimeType, params?: GeoFilterParams): Promise<HotspotResponse[]> => {
    const res = await pacClient.get<HotspotResponse[]>(`/api/v1/geo/crime-type/${crimeType}`, { params });
    return res.data;
  },

  /** Aggregate spatial statistics. */
  statistics: async (params?: GeoFilterParams): Promise<GeoStatisticsResponse> => {
    const res = await pacClient.get<GeoStatisticsResponse>("/api/v1/geo/statistics", { params });
    return res.data;
  },
};
