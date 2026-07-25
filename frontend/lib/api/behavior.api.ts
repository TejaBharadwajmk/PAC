import { pacClient } from "@/lib/api/pacClient";
import type {
  BehaviourProfileResponse, BehaviourStatisticsResponse,
} from "@/types/api.types";

export const behaviorApi = {
  /** Get behavioral profile for a criminal. */
  criminalProfile: async (criminalId: string): Promise<BehaviourProfileResponse> => {
    const res = await pacClient.get<BehaviourProfileResponse>(`/api/v1/behavior/criminal/${criminalId}`);
    return res.data;
  },

  /** Get high-risk behavioral profiles list. */
  highRiskProfiles: async (minViolence = 0.6, limit = 20): Promise<BehaviourProfileResponse[]> => {
    const res = await pacClient.get<BehaviourProfileResponse[]>("/api/v1/behavior/high-risk", {
      params: { min_violence: minViolence, limit },
    });
    return res.data;
  },

  /** Behavior engine statistics. */
  statistics: async (): Promise<BehaviourStatisticsResponse> => {
    const res = await pacClient.get<BehaviourStatisticsResponse>("/api/v1/behavior/statistics");
    return res.data;
  },
};
