import { pacClient } from "@/lib/api/pacClient";
import type {
  AssistantChatRequest, AssistantChatResponse,
  ReportRequest, ReportResponse, AssistantHealthResponse,
} from "@/types/api.types";

export const assistantApi = {
  /** General investigation question. */
  chat: async (data: AssistantChatRequest): Promise<AssistantChatResponse> => {
    const res = await pacClient.post<AssistantChatResponse>("/api/v1/assistant/chat", data);
    return res.data;
  },

  /** Full investigation briefing using all PAC modules. */
  investigationSummary: async (params: {
    crime_id?: string; criminal_id?: string;
    district?: string; gang_name?: string; session_id?: string;
  }): Promise<AssistantChatResponse> => {
    const res = await pacClient.post<AssistantChatResponse>("/api/v1/assistant/investigation-summary", params);
    return res.data;
  },

  /** District patrol recommendations. */
  patrolBriefing: async (district: string, session_id?: string): Promise<AssistantChatResponse> => {
    const res = await pacClient.post<AssistantChatResponse>("/api/v1/assistant/patrol-briefing", {
      district,
      session_id: session_id ?? "patrol",
    });
    return res.data;
  },

  /** Analytical summary for a specific crime. */
  crimeSummary: async (crime_id: string, session_id?: string): Promise<AssistantChatResponse> => {
    const res = await pacClient.post<AssistantChatResponse>("/api/v1/assistant/crime-summary", {
      crime_id,
      session_id: session_id ?? "crime",
    });
    return res.data;
  },

  /** Criminal intelligence profile brief. */
  criminalSummary: async (criminal_id: string, session_id?: string): Promise<AssistantChatResponse> => {
    const res = await pacClient.post<AssistantChatResponse>("/api/v1/assistant/criminal-summary", {
      criminal_id,
      session_id: session_id ?? "criminal",
    });
    return res.data;
  },

  /** Generate a structured intelligence report. */
  generateReport: async (data: ReportRequest): Promise<ReportResponse> => {
    const res = await pacClient.post<ReportResponse>("/api/v1/assistant/report", data);
    return res.data;
  },

  /** LLM provider health check. */
  health: async (): Promise<AssistantHealthResponse> => {
    const res = await pacClient.get<AssistantHealthResponse>("/api/v1/assistant/health");
    return res.data;
  },
};
