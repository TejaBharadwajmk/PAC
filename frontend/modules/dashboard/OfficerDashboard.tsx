"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Plus, FileText, RefreshCw, Bot } from "lucide-react";
import { useSessionStore } from "@/lib/stores/useSessionStore";
import { crimesApi }       from "@/lib/api/crimes.api";
import { IntelCard }       from "@/components/intelligence/IntelCard";
import { RiskBadge }       from "@/components/intelligence/RiskBadge";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { CRIME_TYPE_LABELS, CRIME_STATUS_LABELS, STALE_TIME } from "@/lib/utils/constants";
import { severityToRiskLevel } from "@/lib/utils/riskLevel";
import { format } from "date-fns";

export default function OfficerDashboard() {
  const { user } = useSessionStore();

  const { data: myCases, isLoading } = useQuery({
    queryKey: ["crimes", "my-cases", 1],
    queryFn:  () => crimesApi.myCases({ page: 1, page_size: 10 }),
    staleTime: STALE_TIME.crimes,
  });

  const safeItems   = Array.isArray(myCases?.items) ? myCases.items : [];
  const openCases   = safeItems.filter((c) => !["solved", "closed"].includes(c.status));
  const closedCases = safeItems.filter((c) => ["solved", "closed"].includes(c.status));

  return (
    <div className="p-6 flex flex-col gap-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-bold text-[#e6edf3]">
            Good {getGreeting()}, {user?.full_name.split(" ")[0]}
          </h1>
          <p className="text-[13px] text-[#8b949e] mt-0.5">
            {user?.district ?? "Karnataka"} · {user?.police_station ?? "Police"} ·{" "}
            <span className="font-mono">{user?.badge_number}</span>
          </p>
        </div>
        <Link
          href="/crimes/new"
          className="flex items-center gap-2 px-4 py-2 bg-[#1f6feb] hover:bg-[#388bfd] text-white text-[13px] font-semibold rounded transition-colors"
        >
          <Plus size={14} />
          Register FIR
        </Link>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <IntelCard
          title="Total My Cases"
          value={myCases?.total ?? 0}

          icon={<FileText size={16} />}
          severity="info"
        />
        <IntelCard
          title="Open Cases"
          value={openCases.length}
          icon={<RefreshCw size={16} />}
          severity={openCases.length > 5 ? "high" : "moderate"}
        />
        <IntelCard
          title="Resolved Cases"
          value={closedCases.length}
          icon={<FileText size={16} />}
          severity="low"
        />
        <IntelCard
          title="AI Assistant"
          value="Ready"
          icon={<Bot size={16} />}
          severity="info"
          href="/assistant"
        />
      </div>

      {/* Cases Table */}
      <div className="pac-card flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-[#e6edf3]">My Registered Cases</h2>
          <Link
            href="/crimes?registered_by=me"
            className="text-[12px] text-[#58a6ff] hover:underline"
          >
            View all →
          </Link>
        </div>

        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : !myCases?.items.length ? (
          <div className="py-12 text-center">
            <FileText size={32} className="text-[#484f58] mx-auto mb-3" />
            <p className="text-[13px] text-[#8b949e]">No cases registered yet.</p>
            <Link href="/crimes/new" className="text-[12px] text-[#58a6ff] hover:underline mt-1 inline-block">
              Register your first FIR →
            </Link>
          </div>
        ) : (
          <table className="pac-table">
            <thead>
              <tr>
                <th className="text-left">FIR Number</th>
                <th className="text-left">Type</th>
                <th className="text-left">Severity</th>
                <th className="text-left">Status</th>
                <th className="text-left">District</th>
                <th className="text-left">Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {myCases.items.map((crime) => (
                <tr
                  key={crime.id}
                  onClick={() => window.location.href = `/crimes/${crime.id}`}
                >
                  <td>
                    <span className="font-mono text-[#58a6ff] text-[12px]">
                      {crime.fir_number}
                    </span>
                  </td>
                  <td className="text-[#c9d1d9]">
                    {CRIME_TYPE_LABELS[crime.crime_type] ?? crime.crime_type}
                  </td>
                  <td>
                    <RiskBadge level={severityToRiskLevel(crime.severity)} size="sm" />
                  </td>
                  <td>
                    <span className="text-[12px] text-[#8b949e]">
                      {CRIME_STATUS_LABELS[crime.status] ?? crime.status}
                    </span>
                  </td>
                  <td className="text-[#c9d1d9]">{crime.district}</td>
                  <td className="text-[#8b949e] font-mono text-[12px]">
                    {format(new Date(crime.occurred_at), "dd MMM yyyy")}
                  </td>
                  <td>
                    <Link
                      href={`/crimes/${crime.id}`}
                      className="text-[12px] text-[#58a6ff] hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* AI Quick Launch */}
      <div className="pac-card border-[rgba(188,140,255,0.3)] bg-[rgba(188,140,255,0.04)]">
        <div className="flex items-start gap-3">
          <Bot size={20} className="text-[#bc8cff] flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-[14px] font-semibold text-[#e6edf3] mb-1">AI Investigation Assistant</p>
            <p className="text-[12px] text-[#8b949e] mb-3">
              Ask about case status, crime patterns, or get operational recommendations for your district.
            </p>
            <Link
              href="/assistant"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded bg-[rgba(188,140,255,0.15)] text-[#bc8cff] border border-[rgba(188,140,255,0.4)] hover:bg-[rgba(188,140,255,0.2)] transition-colors"
            >
              Open Assistant →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 17) return "afternoon";
  return "evening";
}
