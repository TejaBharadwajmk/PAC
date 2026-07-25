"use client";

import { useState } from "react";
import { useQuery }  from "@tanstack/react-query";
import { predictionsApi } from "@/lib/api/predictions.api";
import { RiskBadge }       from "@/components/intelligence/RiskBadge";
import { ConfidenceMeter } from "@/components/intelligence/ConfidenceMeter";
import { EvidenceList }    from "@/components/intelligence/EvidenceList";
import { RecommendationList } from "@/components/intelligence/RecommendationCard";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { KARNATAKA_DISTRICTS, STALE_TIME } from "@/lib/utils/constants";
import { scoreToPercent }  from "@/lib/utils/riskLevel";
import { TrendingUp, AlertTriangle, Shield, Search, Map, Users } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export default function PredictionsPage() {
  const [activeTab, setActiveTab] = useState<"criminal" | "district" | "gang">("criminal");
  const [criminalId, setCriminalId] = useState("");
  const [district, setDistrict]     = useState<string>(KARNATAKA_DISTRICTS[0]);
  const [gangName, setGangName]     = useState("");

  // Statistics
  const { data: stats } = useQuery({
    queryKey:  ["predictions", "statistics"],
    queryFn:   predictionsApi.statistics,
    staleTime: STALE_TIME.predictions,
  });

  // Criminal Prediction Query
  const { data: crimPred, isFetching: crimLoading, refetch: getCrimPred } = useQuery({
    queryKey:  ["predictions", "criminal", criminalId],
    queryFn:   () => predictionsApi.criminal(criminalId),
    enabled:   false,
    staleTime: STALE_TIME.predictions,
  });

  // District Prediction Query
  const { data: distPred, isLoading: distLoading } = useQuery({
    queryKey:  ["predictions", "district", district],
    queryFn:   () => predictionsApi.district(district),
    enabled:   activeTab === "district",
    staleTime: STALE_TIME.predictions,
  });

  // Gang Prediction Query
  const { data: gangPred, isFetching: gangLoading, refetch: getGangPred } = useQuery({
    queryKey:  ["predictions", "gang", gangName],
    queryFn:   () => predictionsApi.gang(gangName),
    enabled:   false,
    staleTime: STALE_TIME.predictions,
  });

  return (
    <div className="p-6 flex flex-col gap-6 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="text-[18px] font-bold text-[#e6edf3] flex items-center gap-2">
          <TrendingUp size={22} className="text-[#f85149]" />
          Predictive Intelligence & Threat Assessment Engine
        </h1>
        <p className="text-[13px] text-[#8b949e] mt-0.5">
          Statistical risk scoring, recidivism modeling, gang threat indices, and district crime forecasts
        </p>
      </div>

      {/* Overview Statistics Row */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="pac-card flex flex-col gap-2 border-[#f85149]/40">
            <p className="text-[10px] font-mono text-[#8b949e] uppercase">Total Profiles Modelled</p>
            <p className="text-[22px] font-mono font-bold text-[#e6edf3]">{stats.total_criminal_predictions}</p>
          </div>
          <div className="pac-card flex flex-col gap-2 border-[#e98d30]/40">
            <p className="text-[10px] font-mono text-[#8b949e] uppercase">Avg Criminal Risk Index</p>
            <p className="text-[22px] font-mono font-bold text-[#e98d30]">{scoreToPercent(stats.average_criminal_risk_score)}</p>
          </div>
          <div className="pac-card flex flex-col gap-2 border-[#f85149]/40">
            <p className="text-[10px] font-mono text-[#8b949e] uppercase">Critical Risk Count</p>
            <p className="text-[22px] font-mono font-bold text-[#f85149]">{stats.risk_level_distribution.CRITICAL || 0}</p>
          </div>
          <div className="pac-card flex flex-col gap-2 border-[#d29922]/40">
            <p className="text-[10px] font-mono text-[#8b949e] uppercase">High Risk Count</p>
            <p className="text-[22px] font-mono font-bold text-[#d29922]">{stats.risk_level_distribution.HIGH || 0}</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#30363d] gap-2">
        {[
          { key: "criminal", label: "Criminal Recidivism Risk", icon: Users },
          { key: "district", label: "District Risk Index",      icon: Map },
          { key: "gang",     label: "Gang Threat Index",        icon: Shield },
        ].map((t) => {
          const Icon = t.icon;
          const active = activeTab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key as "criminal" | "district" | "gang")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-[13px] font-semibold border-b-2 transition-colors",
                active
                  ? "border-[#f85149] text-[#f85149] bg-[rgba(248,81,73,0.1)]"
                  : "border-transparent text-[#8b949e] hover:text-[#e6edf3]",
              )}
            >
              <Icon size={14} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Criminal Risk */}
      {activeTab === "criminal" && (
        <div className="flex flex-col gap-4 animate-fade-in">
          <form
            onSubmit={(e) => { e.preventDefault(); if (criminalId) getCrimPred(); }}
            className="pac-card flex flex-col gap-3"
          >
            <div className="flex gap-3">
              <input
                type="text"
                value={criminalId}
                onChange={(e) => setCriminalId(e.target.value)}
                placeholder="Enter Criminal UUID to calculate risk score…"
                className="flex-1 bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] font-mono focus:outline-none focus:border-[#f85149]"
              />
              <button
                type="submit"
                disabled={crimLoading || !criminalId}
                className="px-4 py-2 bg-[#f85149] text-white text-[13px] font-semibold rounded hover:bg-[#d93830] disabled:opacity-40"
              >
                {crimLoading ? "Calculating…" : "Calculate Risk"}
              </button>
            </div>

            {/* Quick Sample Target Chips */}
            <div className="flex items-center gap-2 text-[11px] font-mono text-[#8b949e]">
              <span>Sample Targets:</span>
              {[
                { name: "Raju Kamble (15 Cases)", id: "8867bf62-02b7-4d61-a36f-632b6a04c6f1" },
                { name: "Prakash Chinnaswamy", id: "8b7236af-2ee8-465c-8676-8b576efc89dd" },
                { name: "Sanjay Kumar Rao", id: "313a2330-000b-42a7-99d6-cddca2bcd985" },
                { name: "Lokesh Hegde", id: "00187804-adb9-4979-86b5-f019bcb3a5cf" },
              ].map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => { setCriminalId(c.id); setTimeout(() => getCrimPred(), 50); }}
                  className="px-2 py-0.5 bg-[#161b22] border border-[#30363d] rounded text-[#58a6ff] hover:bg-[#21262d] transition-colors"
                >
                  {c.name}
                </button>
              ))}
            </div>
          </form>


          {crimPred && (
            <div className="pac-card flex flex-col gap-4 border-[#f85149]/40">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] text-[#8b949e] uppercase font-mono">Entity Target</p>
                  <p className="text-[16px] font-bold text-[#e6edf3] font-mono">{crimPred.entity_id}</p>
                </div>
                <RiskBadge level={crimPred.risk_level ?? "HIGH"} size="md" />
              </div>

              <div className="p-4 bg-[#0d1117] rounded border border-[#30363d] flex items-center justify-between">
                <div>
                  <p className="text-[11px] text-[#8b949e] uppercase font-mono">Prediction Index Score</p>
                  <p className="text-[28px] font-mono font-bold text-[#f85149]">
                    {scoreToPercent(crimPred.prediction_score)}
                  </p>
                </div>
                <ConfidenceMeter score={crimPred.confidence} className="w-48" />
              </div>

              {/* 9 Weighted Score Breakdown Components */}
              {Object.keys(crimPred.score_breakdown).length > 0 && (
                <div>
                  <p className="text-[11px] font-semibold uppercase text-[#8b949e] mb-2 font-mono">
                    Weighted Factors Breakdown
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-[12px]">
                    {Object.entries(crimPred.score_breakdown).map(([k, val]) => (
                      <div key={k} className="p-2 bg-[#0d1117] rounded border border-[#30363d] flex justify-between font-mono">
                        <span className="text-[#8b949e] capitalize">{k.replace("_", " ")}:</span>
                        <span className="text-[#e6edf3] font-bold">{(val * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <EvidenceList items={crimPred.evidence} title="Traceable Evidence Facts" variant="evidence" />
              <RecommendationList items={crimPred.recommendations} title="Operational Recommendations" />
            </div>
          )}
        </div>
      )}

      {/* Tab 2: District Risk */}
      {activeTab === "district" && (
        <div className="flex flex-col gap-4 animate-fade-in">
          <div className="pac-card flex items-center gap-3">
            <span className="text-[13px] font-semibold text-[#8b949e]">Select District:</span>
            <select
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] text-[#e6edf3] px-3 py-1.5 focus:outline-none focus:border-[#f85149]"
            >
              {KARNATAKA_DISTRICTS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {distLoading ? <LoadingSkeleton variant="card" /> : distPred ? (
            <div className="pac-card flex flex-col gap-4 border-[#e98d30]/40">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-[16px] font-bold text-[#e6edf3]">{distPred.district} District Risk Assessment</h2>
                  <p className="text-[12px] text-[#8b949e]">{distPred.crime_volume} crimes · {distPred.hotspot_count} hotspots</p>
                </div>
                <RiskBadge level={distPred.risk_level} size="md" />
              </div>

              <div className="p-4 bg-[#0d1117] rounded border border-[#30363d]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[12px] text-[#8b949e]">District Risk Index</span>
                  <span className="text-[20px] font-mono font-bold text-[#e98d30]">{scoreToPercent(distPred.risk_score)}</span>
                </div>
                <ConfidenceMeter score={distPred.confidence} />
              </div>

              <EvidenceList items={distPred.evidence} title="District Evidence Facts" />
              <RecommendationList items={distPred.recommendations} title="District Patrol Recommendations" />
            </div>
          ) : null}
        </div>
      )}

      {/* Tab 3: Gang Threat */}
      {activeTab === "gang" && (
        <div className="flex flex-col gap-4 animate-fade-in">
          <form
            onSubmit={(e) => { e.preventDefault(); if (gangName) getGangPred(); }}
            className="pac-card flex flex-col gap-3"
          >
            <div className="flex gap-3">
              <input
                type="text"
                value={gangName}
                onChange={(e) => setGangName(e.target.value)}
                placeholder="Enter Gang Name (e.g. D-Company)…"
                className="flex-1 bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] focus:outline-none focus:border-[#bc8cff]"
              />
              <button
                type="submit"
                disabled={gangLoading || !gangName}
                className="px-4 py-2 bg-[#bc8cff] text-[#0d1117] text-[13px] font-bold rounded hover:bg-[#c8a0ff] disabled:opacity-40"
              >
                {gangLoading ? "Assessing…" : "Assess Threat"}
              </button>
            </div>

            {/* Quick Sample Gang Chips */}
            <div className="flex items-center gap-2 text-[11px] font-mono text-[#8b949e]">
              <span>Sample Gangs:</span>
              {["Highway Dacoits", "Tech Fraud Gang", "D-Company"].map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => { setGangName(g); setTimeout(() => getGangPred(), 50); }}
                  className="px-2 py-0.5 bg-[#161b22] border border-[#30363d] rounded text-[#bc8cff] hover:bg-[#21262d] transition-colors"
                >
                  {g}
                </button>
              ))}
            </div>
          </form>


          {gangPred && (
            <div className="pac-card flex flex-col gap-4 border-[#bc8cff]/40">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-[16px] font-bold text-[#e6edf3]">{gangPred.gang_name} Threat Profile</h2>
                  <p className="text-[12px] text-[#8b949e]">{gangPred.member_count} members · {gangPred.crime_count} crimes</p>
                </div>
                <RiskBadge level={gangPred.threat_level} size="md" />
              </div>

              <EvidenceList items={gangPred.evidence} title="Gang Intelligence Evidence" />
              <RecommendationList items={gangPred.recommendations} title="Intervention Recommendations" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
