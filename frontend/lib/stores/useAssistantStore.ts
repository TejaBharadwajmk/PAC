"use client";

import { create } from "zustand";
import type { ChatMessage, AssistantContext } from "@/types/api.types";

interface AssistantState {
  sessionId:  string;
  context:    AssistantContext;
  messages:   ChatMessage[];
  isLoading:  boolean;
  activePanel: "evidence" | "recommendations" | "followup";

  // Actions
  setContext:       (ctx: Partial<AssistantContext>) => void;
  clearContext:     () => void;
  addMessage:       (msg: ChatMessage) => void;
  setLoading:       (loading: boolean) => void;
  clearSession:     () => void;
  setActivePanel:   (panel: "evidence" | "recommendations" | "followup") => void;
  newSession:       () => void;
}

let _sessionCounter = 1;

export const useAssistantStore = create<AssistantState>()((set) => ({
  sessionId:   `session-${Date.now()}`,
  context:     {},
  messages:    [],
  isLoading:   false,
  activePanel: "evidence",

  setContext: (ctx) =>
    set((s) => ({ context: { ...s.context, ...ctx } })),

  clearContext: () =>
    set({ context: {} }),

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  setLoading: (loading) =>
    set({ isLoading: loading }),

  clearSession: () =>
    set({ messages: [], context: {}, isLoading: false }),

  setActivePanel: (panel) =>
    set({ activePanel: panel }),

  newSession: () =>
    set({
      sessionId: `session-${Date.now()}-${_sessionCounter++}`,
      messages:  [],
      context:   {},
      isLoading: false,
    }),
}));
