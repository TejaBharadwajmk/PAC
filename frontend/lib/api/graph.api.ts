import { pacClient } from "@/lib/api/pacClient";
import type {
  NetworkGraphResponse, GraphStatisticsResponse, MessageResponse,
} from "@/types/api.types";

export const graphApi = {
  /** Get 1-hop or 2-hop criminal network graph centered on a criminal. */
  network: async (criminalId: string, depth = 1): Promise<NetworkGraphResponse> => {
    const res = await pacClient.get<NetworkGraphResponse>(`/api/v1/graph/network/${criminalId}`, {
      params: { depth },
    });
    return res.data;
  },

  /** Get crime graph centered on a crime FIR. */
  crimeGraph: async (crimeId: string): Promise<NetworkGraphResponse> => {
    const res = await pacClient.get<NetworkGraphResponse>(`/api/v1/graph/crime/${crimeId}`);
    return res.data;
  },

  /** Find shortest path between two criminals in Neo4j. */
  shortestPath: async (sourceId: string, targetId: string): Promise<NetworkGraphResponse> => {
    const res = await pacClient.get<NetworkGraphResponse>("/api/v1/graph/shortest-path", {
      params: { source_id: sourceId, target_id: targetId },
    });
    return res.data;
  },

  /** Graph statistics (total nodes, edges, density). */
  statistics: async (): Promise<GraphStatisticsResponse> => {
    const res = await pacClient.get<GraphStatisticsResponse>("/api/v1/graph/statistics");
    return res.data;
  },

  /** Manually trigger Neo4j sync for an entity. */
  sync: async (entityType: "crime" | "criminal", entityId: string): Promise<MessageResponse> => {
    const payload = entityType === "crime" ? { crime_ids: [entityId] } : { criminal_ids: [entityId] };
    const res = await pacClient.post<MessageResponse>("/api/v1/graph/sync", payload);
    return res.data;
  },
};
