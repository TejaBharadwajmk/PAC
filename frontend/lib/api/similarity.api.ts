import { pacClient } from "@/lib/api/pacClient";
import type {
  SimilarityMatch, SimilaritySearchRequest, SimilaritySearchResponse,
} from "@/types/api.types";

export const similarityApi = {
  /** MO text similarity search across all Crime DNA embeddings. */
  search: async (data: SimilaritySearchRequest): Promise<SimilaritySearchResponse> => {
    const res = await pacClient.post<SimilaritySearchResponse>("/api/v1/similarity/search", data);
    return res.data;
  },

  /** Get top similarity matches for a specific crime. */
  getForCrime: async (crimeId: string, top_k = 10, min_score = 0.5): Promise<SimilarityMatch[]> => {
    const res = await pacClient.get<SimilarityMatch[]>(`/api/v1/similarity/crime/${crimeId}`, {
      params: { top_k, min_score },
    });
    return res.data;
  },
};

