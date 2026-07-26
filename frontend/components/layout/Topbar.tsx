"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, LogOut, Shield, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { useSessionStore } from "@/lib/stores/useSessionStore";

const ROLE_LABELS: Record<string, string> = {
  officer:    "Officer",
  analyst:    "Analyst",
  supervisor: "Supervisor",
  admin:      "Administrator",
};

const ROLE_COLOURS: Record<string, string> = {
  officer:    "#58a6ff",
  analyst:    "#bc8cff",
  supervisor: "#d29922",
  admin:      "#f85149",
};

export function Topbar() {
  const router                  = useRouter();
  const { user, logout }        = useSessionStore();
  const [search, setSearch]     = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = search.trim();
    if (!q) return;
    if (q.match(/^FIR/i)) {
      router.push(`/crimes/fir/${encodeURIComponent(q)}`);
    } else {
      router.push(`/criminals?search=${encodeURIComponent(q)}`);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      document.cookie = "pac_role=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;";
      document.cookie = "pac_refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;";
      logout();
      router.push("/login");
    }
  };

  const roleColour = ROLE_COLOURS[user?.role ?? "officer"] ?? "#8b949e";

  return (
    <header className="app-shell-topbar flex items-center justify-between px-4 bg-[#0d1117] border-b border-[#30363d] z-50">
      {/* Left: global search */}
      <form onSubmit={handleSearch} className="flex items-center">
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8b949e]"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search FIR number or criminal name…"
            className={cn(
              "w-72 bg-[#161b22] border border-[#30363d] rounded text-[13px]",
              "pl-9 pr-4 py-1.5 text-[#e6edf3] placeholder-[#484f58]",
              "focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#58a6ff]/30",
              "transition-all duration-150",
            )}
          />
        </div>
      </form>

      {/* Centre: enterprise technology badges & system status */}
      <div className="hidden md:flex items-center gap-3 text-[#8b949e]">
        <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#161b22] border border-[#238636]/40 text-[#3fb950] font-mono text-[10px] font-bold">
          <span className="w-1.5 h-1.5 rounded-full bg-[#3fb950] animate-pulse" />
          LIVE SYSTEM
        </div>
        <div className="flex items-center gap-1 text-[10px] font-mono text-[#8b949e]">
          <Shield size={11} className="text-[#1f6feb]" />
          <span>PostgreSQL • Neo4j • Redis</span>
        </div>
        <div className="flex items-center gap-1 font-mono text-[10px] text-[#bc8cff]">
          <span>AI • pgvector • PostGIS</span>
        </div>
      </div>


      {/* Right: user menu */}
      {user && (
        <div className="relative">
          <button
            onClick={() => setMenuOpen((o) => !o)}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded border border-[#30363d] hover:border-[#8b949e] bg-[#161b22] hover:bg-[#21262d] transition-all duration-150"
          >
            <div
              className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold"
              style={{ background: `${roleColour}25`, color: roleColour, border: `1px solid ${roleColour}60` }}
            >
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div className="text-left">
              <p className="text-[12px] font-semibold text-[#e6edf3] leading-tight">
                {user.full_name.split(" ")[0]}
              </p>
              <p
                className="text-[9px] font-mono uppercase tracking-wider leading-tight"
                style={{ color: roleColour }}
              >
                {ROLE_LABELS[user.role]}
              </p>
            </div>
            <ChevronDown size={12} className="text-[#8b949e]" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 w-52 bg-[#161b22] border border-[#30363d] rounded-md shadow-elevated z-50 animate-fade-in overflow-hidden">
              <div className="px-3 py-2.5 border-b border-[#30363d]">
                <p className="text-[12px] font-semibold text-[#e6edf3]">{user.full_name}</p>
                <p className="text-[11px] font-mono text-[#8b949e]">{user.badge_number}</p>
                {user.district && (
                  <p className="text-[11px] text-[#8b949e] mt-0.5">{user.district}</p>
                )}
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-[#f85149] hover:bg-[rgba(248,81,73,0.08)] transition-colors"
              >
                <LogOut size={13} />
                Sign Out
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
