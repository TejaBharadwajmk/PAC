"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery }  from "@tanstack/react-query";
import { Sidebar }   from "@/components/layout/Sidebar";
import { Topbar }    from "@/components/layout/Topbar";
import { useSessionStore } from "@/lib/stores/useSessionStore";
import { authApi }   from "@/lib/api/auth.api";
import { initPacClientTokenStore } from "@/lib/api/pacClient";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router                            = useRouter();
  const { accessToken, setAccessToken, setUser, logout, isAuthenticated } = useSessionStore();

  // Wire Axios client to Zustand store (idempotent)
  useEffect(() => {
    initPacClientTokenStore({ accessToken, setAccessToken, logout });
  }, [accessToken, setAccessToken, logout]);

  // Silent refresh on mount — if no access token but refresh cookie exists,
  // the pacClient interceptor will handle it automatically on the first request.
  // Here we ensure we have a user profile loaded.
  const { isLoading } = useQuery({
    queryKey: ["auth", "me"],
    queryFn:  async () => {
      // Attempt to get a fresh token if not in memory
      if (!accessToken) {
        const refreshRes = await fetch("/api/auth/refresh", { method: "POST" });
        if (!refreshRes.ok) {
          router.push("/login");
          return null;
        }
        const { access_token } = await refreshRes.json();
        setAccessToken(access_token);
      }
      const user = await authApi.me();
      setUser(user);
      return user;
    },
    enabled:   true,
    retry:     false,
    staleTime: 300_000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0d1117]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-[#1f6feb] border-t-transparent rounded-full animate-spin" />
          <p className="text-[13px] text-[#8b949e] font-mono">Authenticating…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Topbar />
      <Sidebar />
      <main className="app-shell-content">
        {children}
      </main>
    </div>
  );
}
