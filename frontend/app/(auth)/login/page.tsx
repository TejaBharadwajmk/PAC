"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm }   from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z }          from "zod";
import { toast }      from "sonner";
import { Shield, Eye, EyeOff, Lock, Hash, AlertCircle } from "lucide-react";
import { useSessionStore } from "@/lib/stores/useSessionStore";
import { authApi }         from "@/lib/api/auth.api";
import { initPacClientTokenStore } from "@/lib/api/pacClient";
import { cn }              from "@/lib/utils/cn";

const loginSchema = z.object({
  badge_number: z.string().min(1, "Badge number is required"),
  password:     z.string().min(1, "Password is required"),
});
type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router                       = useRouter();
  const { login, setAccessToken, logout } = useSessionStore();
  const [showPassword, setShowPass]  = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  // Clear all stale cookies and session state on login mount
  useEffect(() => {
    logout();
    if (typeof window !== "undefined") {
      document.cookie = "pac_role=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Strict;";
      document.cookie = "pac_role=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax;";
      document.cookie = "pac_role=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;";
      fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    }
  }, [logout]);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setServerError(null);
    try {
      // Call BFF proxy — it stores refresh_token in httpOnly cookie
      const res = await fetch("/api/auth/login", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(data),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Authentication failed" }));
        setServerError(err.detail ?? "Invalid badge number or password");
        return;
      }

      const { access_token } = await res.json();

      // Wire token store and set access token in memory first
      setAccessToken(access_token);
      
      // Fetch user profile with the token now set in memory
      const user = await authApi.me();

      // Store in memory session
      login(access_token, user);

      toast.success(`Welcome back, ${user.full_name.split(" ")[0]}`);
      router.push("/");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed";
      setServerError(msg);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] flex items-center justify-center p-4">
      {/* Background grid pattern */}
      <div
        className="fixed inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(#30363d 1px, transparent 1px), linear-gradient(90deg, #30363d 1px, transparent 1px)`,
          backgroundSize: "40px 40px",
        }}
      />

      <div className="w-full max-w-sm relative z-10">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-[#1f6feb] mb-4 shadow-[0_0_24px_rgba(31,111,235,0.4)]">
            <Shield size={28} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-[#e6edf3] mb-1">
            Police Analytics Core
          </h1>
          <p className="text-[13px] text-[#8b949e]">
            Karnataka Law Enforcement — Authorised Access Only
          </p>
        </div>

        {/* Form Card */}
        <div className="pac-card-elevated">
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
            <div className="text-center border-b border-[#30363d] pb-4 mb-2">
              <p className="text-[11px] text-[#484f58] uppercase tracking-widest font-mono">
                Officer Authentication
              </p>
            </div>

            {/* Server error */}
            {serverError && (
              <div className="flex items-center gap-2 p-3 rounded-md bg-[rgba(248,81,73,0.1)] border border-[rgba(248,81,73,0.4)] text-[#f85149] text-[13px] animate-fade-in">
                <AlertCircle size={14} className="flex-shrink-0" />
                <span>{serverError}</span>
              </div>
            )}

            {/* Badge Number */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="badge_number" className="text-[12px] font-semibold text-[#8b949e] uppercase tracking-wider">
                Badge Number
              </label>
              <div className="relative">
                <Hash size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8b949e]" />
                <input
                  id="badge_number"
                  type="text"
                  placeholder="e.g. KAR-1001"
                  autoComplete="username"
                  {...register("badge_number")}
                  className={cn(
                    "w-full pl-9 pr-4 py-2.5 rounded bg-[#0d1117] border text-[13px] font-mono",
                    "text-[#e6edf3] placeholder-[#484f58]",
                    "focus:outline-none focus:ring-1 transition-all duration-150",
                    errors.badge_number
                      ? "border-[#f85149] focus:ring-[rgba(248,81,73,0.3)]"
                      : "border-[#30363d] focus:border-[#58a6ff] focus:ring-[rgba(88,166,255,0.3)]",
                  )}
                />
              </div>
              {errors.badge_number && (
                <p className="text-[11px] text-[#f85149]">{errors.badge_number.message}</p>
              )}
            </div>

            {/* Password */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="password" className="text-[12px] font-semibold text-[#8b949e] uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8b949e]" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  {...register("password")}
                  className={cn(
                    "w-full pl-9 pr-10 py-2.5 rounded bg-[#0d1117] border text-[13px]",
                    "text-[#e6edf3] placeholder-[#484f58]",
                    "focus:outline-none focus:ring-1 transition-all duration-150",
                    errors.password
                      ? "border-[#f85149] focus:ring-[rgba(248,81,73,0.3)]"
                      : "border-[#30363d] focus:border-[#58a6ff] focus:ring-[rgba(88,166,255,0.3)]",
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8b949e] hover:text-[#e6edf3] transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              {errors.password && (
                <p className="text-[11px] text-[#f85149]">{errors.password.message}</p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting}
              className={cn(
                "w-full py-2.5 rounded font-semibold text-[13px] transition-all duration-150 mt-1",
                "bg-[#1f6feb] hover:bg-[#388bfd] text-white",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "focus:outline-none focus:ring-2 focus:ring-[#58a6ff]/40",
              )}
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Authenticating…
                </span>
              ) : (
                "Sign In"
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-[11px] text-[#484f58] mt-6 font-mono">
          Unauthorised access is a criminal offence under the IT Act 2000.
        </p>
      </div>
    </div>
  );
}
