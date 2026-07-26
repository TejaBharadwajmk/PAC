"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { geoApi }         from "@/lib/api/geo.api";
import { predictionsApi } from "@/lib/api/predictions.api";
import { crimesApi }      from "@/lib/api/crimes.api";
import { assistantApi }   from "@/lib/api/assistant.api";
import { IntelCard }           from "@/components/intelligence/IntelCard";
import { RiskBadge }           from "@/components/intelligence/RiskBadge";
import { ConfidenceMeter }     from "@/components/intelligence/ConfidenceMeter";
import { EvidenceList }        from "@/components/intelligence/EvidenceList";
import { RecommendationList }  from "@/components/intelligence/RecommendationCard";
import { SourceChipList }      from "@/components/intelligence/SourceChip";
import { LoadingSkeleton }     from "@/components/common/LoadingSkeleton";
import { KARNATAKA_DISTRICTS, CRIME_TYPE_LABELS, STALE_TIME } from "@/lib/utils/constants";
import { severityToRiskLevel, scoreToPercent } from "@/lib/utils/riskLevel";
import { format } from "date-fns";
import {
  Map, TrendingUp, AlertTriangle, Users, Briefcase, ChevronRight,
  Bot, RefreshCw, Activity,
} from "lucide-react";

export default function SupervisorDashboard() {
  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);
  const [briefingDistrict, setBriefingDistrict] = useState<string>("");

  // Core data
  const { data: geoStats } = useQuery({
    queryKey:  ["geo", "statistics"],
    queryFn:   () => geoApi.statistics(),
    staleTime: STALE_TIME.hotspots,
  });

  const { data: predStats } = useQuery({
    queryKey:  ["predictions", "statistics"],
    queryFn:   () => predictionsApi.statistics(),
    staleTime: STALE_TIME.predictions,
  });

  const { data: allCrimes } = useQuery({
    queryKey:  ["crimes", "list", { page: 1, page_size: 20 }],
    queryFn:   () => crimesApi.list({ page: 1, page_size: 20 }),
    staleTime: STALE_TIME.crimes,
  });

  const { data: criticalCrimes } = useQuery({
    queryKey:  ["crimes", "critical-supervisor"],
    queryFn:   () => crimesApi.list({ severity: "critical", page: 1, page_size: 5 }),
    staleTime: STALE_TIME.crimes,
  });

  // District-specific queries
  const { data: districtHotspots, isLoading: hotspotLoading } = useQuery({
    queryKey:  ["geo", "district", selectedDistrict],
    queryFn:   () => geoApi.districtHotspots(selectedDistrict!),
    enabled:   !!selectedDistrict,
    staleTime: STALE_TIME.hotspots,
  });

  const { data: districtRisk, isLoading: riskLoading } = useQuery({
    queryKey:  ["predictions", "district", selectedDistrict],
    queryFn:   () => predictionsApi.district(selectedDistrict!),
    enabled:   !!selectedDistrict,
    staleTime: STALE_TIME.predictions,
  });

  // Patrol briefing (on demand)
  const { data: patrolBriefing, isLoading: briefingLoading, refetch: fetchBriefing } = useQuery({
    queryKey:  ["assistant", "patrol", briefingDistrict],
    queryFn:   () => assistantApi.patrolBriefing(briefingDistrict),
    enabled:   false,
    staleTime: STALE_TIME.assistant,
  });

  const safeCrimeItems = Array.isArray(allCrimes?.items) ? allCrimes.items : [];
  const solvedCases    = safeCrimeItems.filter((c) => c.status === "solved").length;
  const totalCases     = allCrimes?.total ?? safeCrimeItems.length;

  return (
    <div className="p-6 flex flex-col gap-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-bold text-[#e6edf3]">Command Centre</h1>
          <p className="text-[13px] text-[#8b949e] mt-0.5 flex items-center gap-2">
            <span className="inline-flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#3fb950] animate-pulse-slow" />
              Live Intelligence
            </span>
            · Supervisor View · {format(new Date(), "dd MMM yyyy, HH:mm")}
          </p>
        </div>
        <Link
          href="/assistant"
          className="flex items-center gap-2 px-4 py-2 bg-[rgba(188,140,255,0.15)] border border-[rgba(188,140,255,0.4)] text-[#bc8cff] text-[13px] font-semibold rounded hover:bg-[rgba(188,140,255,0.2)] transition-colors"
        >
          <Bot size={14} />
          AI Briefing
        </Link>
      </div>

      {/* KPI Row — 6 cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <IntelCard title="Active Cases"    value={totalCases}                  icon={<Briefcase size={15} />} severity="info" />
        <IntelCard title="Critical Cases"  value={criticalCrimes?.total ?? 0}  icon={<AlertTriangle size={15} />} severity="critical" />
        <IntelCard title="Crime Clusters"  value={geoStats?.total_hotspots_detected ?? 0} icon={<Map size={15} />} severity="high" />


        <IntelCard title="High Risk Criminals" value={predStats?.risk_level_distribution?.HIGH ?? 0} icon={<Users size={15} />} severity="high" href="/predictions" />
        <IntelCard title="Avg Risk Score"  value={scoreToPercent(predStats?.average_criminal_risk_score ?? 0)} icon={<TrendingUp size={15} />} severity="moderate" />
        <IntelCard title="Solved Today"    value={solvedCases}                 icon={<Activity size={15} />} severity="low" />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: District Drill-Down */}
        <div className="lg:col-span-1 flex flex-col gap-4">
          {/* District Selector */}
          <div className="pac-card flex flex-col gap-3">
            <h2 className="text-[13px] font-semibold text-[#e6edf3] flex items-center gap-2">
              <Map size={14} className="text-[#58a6ff]" />
              District Intelligence
            </h2>
            <select
              className="w-full bg-[#0d1117] border border-[#30363d] rounded text-[13px] text-[#e6edf3] px-3 py-2 focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#58a6ff]/30"
              value={selectedDistrict ?? ""}
              onChange={(e) => setSelectedDistrict(e.target.value || null)}
            >
              <option value="">Select a district…</option>
              {KARNATAKA_DISTRICTS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>

            {selectedDistrict && (
              <div className="flex flex-col gap-3 animate-fade-in">
                {riskLoading ? (
                  <LoadingSkeleton variant="card" />
                ) : districtRisk ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-[12px] text-[#8b949e]">Risk Level</span>
                      <RiskBadge level={districtRisk.risk_level} />
                    </div>
                    <ConfidenceMeter score={districtRisk.confidence} />
                    <div className="text-[12px] text-[#8b949e] flex justify-between">
                      <span>{districtRisk.hotspot_count} hotspots</span>
                      <span>{districtRisk.crime_volume} crimes</span>
                    </div>
                    <EvidenceList
                      items={districtRisk.evidence.slice(0, 3)}
                      variant="evidence"
                      title="Evidence"
                    />
                  </>
                ) : null}

                {hotspotLoading ? null : districtHotspots?.length ? (
                  <div>
                    <p className="text-[11px] text-[#8b949e] uppercase tracking-wider font-semibold mb-2">
                      Active Clusters ({districtHotspots.length})
                    </p>
                    {districtHotspots.slice(0, 3).map((h) => (
                      <div key={h.cluster_id} className="flex items-center justify-between py-2 border-b border-[#21262d] last:border-0">
                        <div>
                          <p className="text-[12px] text-[#c9d1d9]">{CRIME_TYPE_LABELS[h.dominant_crime_type] ?? h.dominant_crime_type}</p>
                          <p className="text-[11px] text-[#8b949e] font-mono">{h.crime_count} crimes</p>
                        </div>
                        <span className="text-[11px] font-mono text-[#8b949e]">r={Math.round(h.radius_meters ?? 0)}m</span>

                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            )}
          </div>

          {/* AI Patrol Briefing */}
          <div className="pac-card flex flex-col gap-3">
            <h2 className="text-[13px] font-semibold text-[#e6edf3] flex items-center gap-2">
              <Bot size={14} className="text-[#bc8cff]" />
              AI Patrol Briefing
            </h2>
            <div className="flex gap-2">
              <select
                className="flex-1 bg-[#0d1117] border border-[#30363d] rounded text-[13px] text-[#e6edf3] px-3 py-2 focus:outline-none focus:border-[#bc8cff]"
                value={briefingDistrict}
                onChange={(e) => setBriefingDistrict(e.target.value)}
              >
                <option value="">Select district…</option>
                {KARNATAKA_DISTRICTS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
              <button
                disabled={!briefingDistrict || briefingLoading}
                onClick={() => fetchBriefing()}
                className="px-3 py-2 bg-[rgba(188,140,255,0.15)] border border-[rgba(188,140,255,0.4)] text-[#bc8cff] text-[12px] rounded hover:bg-[rgba(188,140,255,0.2)] disabled:opacity-40 transition-colors"
              >
                {briefingLoading ? <RefreshCw size={13} className="animate-spin" /> : "Get"}
              </button>
            </div>

            {patrolBriefing && (
              <div className="animate-fade-in flex flex-col gap-3">
                <div className="text-[10px] text-[#484f58] uppercase font-mono tracking-wider border border-[rgba(210,153,34,0.3)] rounded-sm px-2 py-1 inline-block text-[#d29922] bg-[rgba(210,153,34,0.1)]">
                  AI-generated · Verify before operational use
                </div>
                <p className="text-[13px] text-[#c9d1d9] leading-relaxed">{patrolBriefing.answer}</p>
                <ConfidenceMeter score={patrolBriefing.confidence} />
                <SourceChipList sources={patrolBriefing.sources} />
                <RecommendationList items={patrolBriefing.recommendations.slice(0, 3)} />
              </div>
            )}
          </div>
        </div>

        {/* Centre + Right: Critical Cases + Risk Table */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {/* Critical Cases */}
          <div className="pac-card flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
                <AlertTriangle size={14} className="text-[#f85149]" />
                Critical Active Cases
                {criticalCrimes?.total ? (
                  <span className="text-[11px] font-mono text-[#f85149] bg-[rgba(248,81,73,0.15)] px-1.5 py-0.5 rounded-sm border border-[rgba(248,81,73,0.4)]">
                    {criticalCrimes.total}
                  </span>
                ) : null}
              </h2>
              <Link href="/crimes?severity=critical" className="text-[12px] text-[#58a6ff] hover:underline flex items-center gap-0.5">
                All <ChevronRight size={12} />
              </Link>
            </div>
            {criticalCrimes?.items.length ? (
              <table className="pac-table">
                <thead>
                  <tr>
                    <th className="text-left">FIR</th>
                    <th className="text-left">Type</th>
                    <th className="text-left">District</th>
                    <th className="text-left">Status</th>
                    <th className="text-left">Date</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {criticalCrimes.items.map((c) => (
                    <tr key={c.id} onClick={() => window.location.href = `/crimes/${c.id}`}>
                      <td><span className="font-mono text-[#f85149] text-[12px]">{c.fir_number}</span></td>
                      <td className="text-[12px] text-[#c9d1d9]">{CRIME_TYPE_LABELS[c.crime_type]}</td>
                      <td className="text-[12px] text-[#8b949e]">{c.district}</td>
                      <td><span className="text-[11px] text-[#8b949e]">{c.status.replace("_", " ")}</span></td>
                      <td className="font-mono text-[11px] text-[#8b949e]">{format(new Date(c.occurred_at), "dd MMM yyyy")}</td>
                      <td>
                        <Link href={`/crimes/${c.id}`} className="text-[12px] text-[#58a6ff] hover:underline" onClick={(e) => e.stopPropagation()}>
                          View →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-[13px] text-[#8b949e] py-6 text-center">No critical cases</p>
            )}
          </div>

          {/* Risk Level Distribution */}
          {predStats && (
            <div className="pac-card flex flex-col gap-3">
              <h2 className="text-[13px] font-semibold text-[#e6edf3] flex items-center gap-2">
                <TrendingUp size={14} className="text-[#bc8cff]" />
                Criminal Risk Distribution
              </h2>
              <div className="grid grid-cols-4 gap-3">
                {(["CRITICAL", "HIGH", "MODERATE", "LOW"] as const).map((level) => {
                  const count = predStats.risk_level_distribution[level] ?? 0;
                  const total = predStats.total_criminal_predictions || 1;
                  const pct   = (count / total) * 100;
                  return (
                    <div key={level} className="flex flex-col items-center gap-1.5">
                      <RiskBadge level={level} size="sm" />
                      <span className="text-[18px] font-bold font-mono text-[#e6edf3]">{count}</span>
                      <div className="w-full h-1 bg-[#21262d] rounded-full">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${pct}%`,
                            background: level === "CRITICAL" ? "#f85149" : level === "HIGH" ? "#e98d30" : level === "MODERATE" ? "#d29922" : "#3fb950",
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
              <p className="text-[11px] text-[#8b949e] text-right">
                Total {predStats.total_criminal_predictions} criminal profiles analysed
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
