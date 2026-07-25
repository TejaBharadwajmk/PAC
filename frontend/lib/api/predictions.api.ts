import { pacClient } from "@/lib/api/pacClient";
import type {
  PredictionResponse, DistrictRiskResponse, GangThreatResponse,
  HotspotForecastResponse, PredictionStatisticsResponse,
} from "@/types/api.types";

export const predictionsApi = {
  /** Criminal recidivism risk score. */
  criminal: async (criminalId: string): Promise<PredictionResponse> => {
    const res = await pacClient.get<PredictionResponse>(`/api/v1/predictions/criminal/${criminalId}`);
    return res.data;
  },

  /** District-level crime risk assessment. */
  district: async (district: string): Promise<DistrictRiskResponse> => {
    const res = await pacClient.get<DistrictRiskResponse>(`/api/v1/predictions/district/${district}`);
    return res.data;
  },

  /** Gang threat assessment. */
  gang: async (gangName: string): Promise<GangThreatResponse> => {
    const res = await pacClient.get<GangThreatResponse>(`/api/v1/predictions/gang/${encodeURIComponent(gangName)}`);
    return res.data;
  },

  /** Hotspot growth forecast. */
  hotspot: async (hotspotId: string): Promise<HotspotForecastResponse> => {
    const res = await pacClient.get<HotspotForecastResponse>(`/api/v1/predictions/hotspot/${hotspotId}`);
    return res.data;
  },

  /** Overall prediction statistics. */
  statistics: async (): Promise<PredictionStatisticsResponse> => {
    const res = await pacClient.get<PredictionStatisticsResponse>("/api/v1/predictions/statistics");
    return res.data;
  },
};
