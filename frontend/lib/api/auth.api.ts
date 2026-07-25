import { pacClient } from "@/lib/api/pacClient";
import type {
  LoginRequest, TokenResponse, UserResponse, UserCreate, UserUpdate,
} from "@/types/api.types";

export const authApi = {
  /** Authenticate via badge + password. Returns token pair. */
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const res = await pacClient.post<TokenResponse>("/api/v1/auth/login", data);
    return res.data;
  },

  /** Get the currently authenticated officer's profile. */
  me: async (): Promise<UserResponse> => {
    const res = await pacClient.get<UserResponse>("/api/v1/auth/me");
    return res.data;
  },

  /** Register a new officer (supervisor/admin only). */
  register: async (data: UserCreate): Promise<UserResponse> => {
    const res = await pacClient.post<UserResponse>("/api/v1/auth/register", data);
    return res.data;
  },

  /** Update an existing user (admin only). */
  update: async (id: string, data: UserUpdate): Promise<UserResponse> => {
    const res = await pacClient.patch<UserResponse>(`/api/v1/auth/users/${id}`, data);
    return res.data;
  },
};
