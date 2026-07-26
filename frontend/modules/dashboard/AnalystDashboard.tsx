"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { geoApi }         from "@/lib/api/geo.api";
import { predictionsApi } from "@/lib/api/predictions.api";
import { crimesApi }      from "@/lib/api/crimes.api";
import { IntelCard }       from "@/components/intelligence/IntelCard";
import { RiskBadge }       from "@/components/intelligence/RiskBadge";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { CRIME_TYPE_LABELS, CRIME_STATUS_LABELS, STALE_TIME } from "@/lib/utils/constants";
import { severityToRiskLevel, scoreToPercent } from "@/lib/utils/riskLevel";
import { format } from "date-fns";
import {
  Map, TrendingUp, AlertTriangle, Dna, Network, BarChart2,
} from "lucide-react";

export default function AnalystDashboard() {
  const { data: geoStats, isLoading: geoLoading } = useQuery({
    queryKey:  ["geo", "statistics"],
    queryFn:   () => geoApi.statistics(),
    staleTime: STALE_TIME.hotspots,
  });

  const { data: predStats, isLoading: predLoading } = useQuery({
    queryKey:  ["predictions", "statistics"],
    queryFn:   () => predictionsApi.statistics(),
    staleTime: STALE_TIME.predictions,
  });

  const { data: recentCrimes, isLoading: crimesLoading } = useQuery({
    queryKey:  ["crimes", "list", { page: 1, page_size: 10 }],
    queryFn:   () => crimesApi.list({ page: 1, page_size: 10 }),
    staleTime: STALE_TIME.crimes,
  });

  const { data: criticalCrimes } = useQuery({
    queryKey:  ["crimes", "critical"],
    queryFn:   () => crimesApi.list({ severity: "critical", page: 1, page_size: 5 }),
    staleTime: STALE_TIME.crimes,
  });

  const avgRisk     = predStats?.average_criminal_risk_score ?? 0;
  const criticalPct = predStats?.risk_level_distribution?.CRITICAL ?? 0;

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl">
      <div>
        <h1 className="text-[18px] font-bold text-[#e6edf3]">Crime Intelligence Dashboard</h1>
        <p className="text-[13px] text-[#8b949e] mt-0.5">Analyst view · Real-time PAC intelligence modules</p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <IntelCard
          title="Total Crimes"
          value={recentCrimes?.total ?? 0}
          icon={<BarChart2 size={15} />}
          severity="info"
        />
        <IntelCard
          title="Crime Clusters"
          value={geoStats?.total_hotspots_detected ?? 0}
          icon={<Map size={15} />}
          severity="moderate"
          href="/geo"
        />
        <IntelCard
          title="Avg Risk Score"
          value={predStats ? scoreToPercent(avgRisk) : "0%"}
          icon={<TrendingUp size={15} />}
          severity={avgRisk > 0.6 ? "high" : avgRisk > 0.3 ? "moderate" : "low"}
          href="/predictions"
        />
        <IntelCard
          title="Critical Profiles"
          value={criticalPct}
          icon={<AlertTriangle size={15} />}
          severity="critical"
          href="/predictions"
        />
        <IntelCard
          title="Top District"
          value={geoStats?.top_hotspot_district ?? "None Detected"}
          icon={<Map size={15} />}
          severity="high"
        />


        <IntelCard
          title="Network Explorer"
          value="Active"
          icon={<Network size={15} />}
          severity="low"
          href="/network"
        />
      </div>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent Crimes Table */}
        <div className="pac-card flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold text-[#e6edf3]">Recent FIRs</h2>
            <Link href="/crimes" className="text-[12px] text-[#58a6ff] hover:underline">View all →</Link>
          </div>
          {crimesLoading ? <LoadingSkeleton variant="table" /> : (
            <table className="pac-table">
              <thead>
                <tr>
                  <th className="text-left">FIR</th>
                  <th className="text-left">Type</th>
                  <th className="text-left">Severity</th>
                  <th className="text-left">District</th>
                </tr>
              </thead>
              <tbody>
                {recentCrimes?.items.slice(0, 8).map((c) => (
                  <tr key={c.id} onClick={() => window.location.href = `/crimes/${c.id}`}>
                    <td><span className="font-mono text-[#58a6ff] text-[12px]">{c.fir_number}</span></td>
                    <td className="text-[12px] text-[#c9d1d9]">{CRIME_TYPE_LABELS[c.crime_type]}</td>
                    <td><RiskBadge level={severityToRiskLevel(c.severity)} size="sm" /></td>
                    <td className="text-[12px] text-[#8b949e]">{c.district}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Critical Cases */}
        <div className="pac-card flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold text-[#e6edf3]">
              Critical Cases
              {criticalCrimes?.total ? (
                <span className="ml-2 text-[11px] font-mono text-[#f85149] bg-[rgba(248,81,73,0.15)] px-1.5 py-0.5 rounded-sm border border-[rgba(248,81,73,0.4)]">
                  {criticalCrimes.total}
                </span>
              ) : null}
            </h2>
            <Link href="/crimes?severity=critical" className="text-[12px] text-[#58a6ff] hover:underline">View all →</Link>
          </div>
          {Array.isArray(criticalCrimes?.items) && criticalCrimes.items.length > 0 ? (
            <div className="flex flex-col gap-2">
              {criticalCrimes.items.map((c) => (
                <Link
                  key={c.id}
                  href={`/crimes/${c.id}`}
                  className="flex items-center justify-between p-3 rounded border border-[rgba(248,81,73,0.3)] bg-[rgba(248,81,73,0.05)] hover:bg-[rgba(248,81,73,0.08)] transition-colors group"
                >
                  <div>
                    <p className="text-[12px] font-mono text-[#f85149] font-semibold">{c.fir_number}</p>
                    <p className="text-[12px] text-[#8b949e]">{CRIME_TYPE_LABELS[c.crime_type]} · {c.district}</p>
                  </div>
                  <span className="text-[11px] text-[#8b949e] font-mono">
                    {format(new Date(c.occurred_at), "dd MMM")}
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-[13px] text-[#8b949e]">No critical cases found</div>
          )}
        </div>
      </div>

      {/* Module Quick Access */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { href: "/dna",        label: "Crime DNA", desc: "Similarity search & embeddings", icon: Dna,           colour: "#58a6ff" },
          { href: "/geo",        label: "Geo Intel", desc: "Hotspot clusters & mapping",     icon: Map,           colour: "#d29922" },
          { href: "/network",    label: "Network",   desc: "Criminal network graph",         icon: Network,       colour: "#3fb950" },
          { href: "/predictions",label: "Predictions",desc: "Risk scores & forecasts",       icon: TrendingUp,    colour: "#bc8cff" },
        ].map((m) => {
          const Icon = m.icon;
          return (
            <Link
              key={m.href}
              href={m.href}
              className="pac-card hover:bg-[#1c2128] hover:border-[#58a6ff]/30 transition-all duration-150 flex flex-col gap-2"
            >
              <Icon size={18} style={{ color: m.colour }} />
              <p className="text-[13px] font-semibold text-[#e6edf3]">{m.label}</p>
              <p className="text-[12px] text-[#8b949e]">{m.desc}</p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
