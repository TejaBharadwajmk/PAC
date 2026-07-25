import { pacClient } from "./pacClient";

export interface AuditLogItem {
  id: string;
  badge_number: string | null;
  action: string;
  endpoint: string;
  method: string;
  query_text: string | null;
  ip_address: string | null;
  status_code: number;
  duration_ms: number;
  timestamp: string;
}

export interface CctnsSyncLogItem {
  id: string;
  records_found: number;
  records_imported: number;
  duplicates_skipped: number;
  status: string;
  error_message: string | null;
  duration_ms: number;
  created_at: string;
}

export const adminApi = {
  getAuditLogs: async (limit = 20): Promise<AuditLogItem[]> => {
    const res = await pacClient.get<AuditLogItem[]>(`/api/v1/audit/logs?limit=${limit}`);
    return res.data;
  },

  getCctnsLogs: async (limit = 10): Promise<CctnsSyncLogItem[]> => {
    const res = await pacClient.get<CctnsSyncLogItem[]>(`/api/v1/cctns/logs?limit=${limit}`);
    return res.data;
  },

  seedCctnsStaging: async (batchSize = 5): Promise<{ status: string; seeded_count: number }> => {
    const res = await pacClient.post<{ status: string; seeded_count: number }>(`/api/v1/cctns/seed-staging?batch_size=${batchSize}`);
    return res.data;
  },

  triggerCctnsSync: async (): Promise<{ status: string; log: CctnsSyncLogItem }> => {
    const res = await pacClient.post<{ status: string; log: CctnsSyncLogItem }>("/api/v1/cctns/sync");
    return res.data;
  },
};
