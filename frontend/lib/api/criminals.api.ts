import { pacClient } from "@/lib/api/pacClient";
import type { CriminalResponse, CriminalListItem } from "@/types/api.types";

export interface CriminalFilterParams {
  district?:    string;
  search?:      string;
  name_search?: string;
  page?:        number;
  page_size?:   number;
}

export const criminalsApi = {
  /** List criminals with search & filter. */
  list: async (params?: CriminalFilterParams): Promise<CriminalListItem[]> => {
    const res = await pacClient.get<CriminalListItem[]>("/api/v1/criminals/", { params });
    return res.data;
  },

  /** Get criminal intelligence dossier by ID. */
  get: async (id: string): Promise<CriminalResponse> => {
    const res = await pacClient.get<CriminalResponse>(`/api/v1/criminals/${id}`);
    return res.data;
  },
};
