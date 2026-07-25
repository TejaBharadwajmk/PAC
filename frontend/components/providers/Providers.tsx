"use client";

import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { useSessionStore } from "@/lib/stores/useSessionStore";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry:              1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function Providers({ children }: { children: React.ReactNode }) {
  const { accessToken, login } = useSessionStore();

  // Restore session on mount if page reloaded
  useEffect(() => {
    if (!accessToken && typeof window !== "undefined") {
      fetch("/api/auth/refresh", { method: "POST" })
        .then((res) => {
          if (res.ok) return res.json();
          return null;
        })
        .then((data) => {
          if (data?.access_token && data?.user) {
            login(data.access_token, data.user);
          }
        })
        .catch(() => {
          // Silent catch — proxy middleware will handle unauthenticated redirects
        });
    }
  }, [accessToken, login]);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="bottom-right"
        theme="dark"
        toastOptions={{
          style: {
            background: "#21262d",
            border:     "1px solid #30363d",
            color:      "#e6edf3",
            fontFamily: "Inter, sans-serif",
            fontSize:   "13px",
          },
        }}
      />
    </QueryClientProvider>
  );
}
