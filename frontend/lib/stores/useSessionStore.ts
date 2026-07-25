"use client";

import { create } from "zustand";
import type { UserResponse } from "@/types/api.types";

interface SessionState {
  // Token stored in memory — never in localStorage
  accessToken: string | null;
  // Full user profile from GET /api/v1/auth/me
  user: UserResponse | null;
  isAuthenticated: boolean;

  // Actions
  setAccessToken: (token: string) => void;
  setUser: (user: UserResponse) => void;
  login: (token: string, user: UserResponse) => void;
  logout: () => void;
}

export const useSessionStore = create<SessionState>()((set) => ({
  accessToken:     null,
  user:            null,
  isAuthenticated: false,

  setAccessToken: (token) =>
    set({ accessToken: token, isAuthenticated: true }),

  setUser: (user) =>
    set({ user }),

  login: (token, user) =>
    set({ accessToken: token, user, isAuthenticated: true }),

  logout: () =>
    set({ accessToken: null, user: null, isAuthenticated: false }),
}));
