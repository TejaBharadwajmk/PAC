import { pacClient } from "@/lib/api/pacClient";
import type {
  CrimeCreate, CrimeUpdate, CrimeResponse, CrimeListItem,
  PaginatedResponse,
} from "@/types/api.types";
import type { CrimeType, CrimeStatus, CrimeSeverity } from "@/types/api.types";

export interface CrimeFilterParams {
  district?:    string;
  crime_type?:  CrimeType;
  status?:      CrimeStatus;
  severity?:    CrimeSeverity;
  from_date?:   string;
  to_date?:     string;
  page?:        number;
  page_size?:   number;
}

export const crimesApi = {
  /** Register a new FIR. */
  register: async (data: CrimeCreate): Promise<CrimeResponse> => {
    const res = await pacClient.post<CrimeResponse>("/api/v1/crimes/", data);
    return res.data;
  },

  /** Paginated list of crimes with optional filters. */
  list: async (params?: CrimeFilterParams): Promise<PaginatedResponse<CrimeListItem>> => {
    const res = await pacClient.get<PaginatedResponse<CrimeListItem>>("/api/v1/crimes/", { params });
    return res.data;
  },

  /** Cases registered by the current officer. */
  myCases: async (params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<CrimeListItem>> => {
    const res = await pacClient.get<PaginatedResponse<CrimeListItem>>("/api/v1/crimes/my-cases", { params });
    return res.data;
  },

  /** Get full crime detail by UUID. */
  get: async (id: string): Promise<CrimeResponse> => {
    const res = await pacClient.get<CrimeResponse>(`/api/v1/crimes/${id}`);
    return res.data;
  },

  /** Get crime detail by FIR number. */
  getByFir: async (firNumber: string): Promise<CrimeResponse> => {
    const res = await pacClient.get<CrimeResponse>(`/api/v1/crimes/fir/${firNumber}`);
    return res.data;
  },

  /** Update a crime record. */
  update: async (id: string, data: CrimeUpdate): Promise<CrimeResponse> => {
    const res = await pacClient.put<CrimeResponse>(`/api/v1/crimes/${id}`, data);
    return res.data;
  },

  /** Delete a crime (admin only). */
  delete: async (id: string): Promise<void> => {
    await pacClient.delete(`/api/v1/crimes/${id}`);
  },
};
