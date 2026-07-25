"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { criminalsApi }   from "@/lib/api/criminals.api";
import { behaviorApi }    from "@/lib/api/behavior.api";
import { predictionsApi } from "@/lib/api/predictions.api";
import { graphApi }       from "@/lib/api/graph.api";
import { assistantApi }   from "@/lib/api/assistant.api";
import { RiskBadge }           from "@/components/intelligence/RiskBadge";
import { ConfidenceMeter }     from "@/components/intelligence/ConfidenceMeter";
import { EvidenceList }        from "@/components/intelligence/EvidenceList";
import { RecommendationList }  from "@/components/intelligence/RecommendationCard";
import { SourceChipList }      from "@/components/intelligence/SourceChip";
import { LoadingSkeleton }     from "@/components/common/LoadingSkeleton";
import { STALE_TIME, CRIME_TYPE_LABELS } from "@/lib/utils/constants";
import { scoreToPercent } from "@/lib/utils/riskLevel";
import {
  User, Shield, Activity, TrendingUp, Network, Bot, ArrowLeft,
  AlertTriangle, Phone, MapPin, Hash, CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";

export default function CriminalDossierPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const criminalId     = resolvedParams.id;

  const [activeTab, setActiveTab] = useState<"overview" | "behavior" | "predictions" | "network">("overview");

  // Primary criminal profile query
  const { data: criminal, isLoading } = useQuery({
    queryKey: ["criminals", "detail", criminalId],
    queryFn:  () => criminalsApi.get(criminalId),
    staleTime: STALE_TIME.criminalDetail,
  });

  // Behaviour profile query
  const { data: behavior } = useQuery({
    queryKey: ["behavior", "criminal", criminalId],
    queryFn:  () => behaviorApi.criminalProfile(criminalId),
    enabled:  activeTab === "behavior" || activeTab === "overview",
    staleTime: STALE_TIME.behaviour,
  });

  // Predictions query
  const { data: prediction } = useQuery({
    queryKey: ["predictions", "criminal", criminalId],
    queryFn:  () => predictionsApi.criminal(criminalId),
    enabled:  activeTab === "predictions" || activeTab === "overview",
    staleTime: STALE_TIME.predictions,
  });

  // Graph network query
  const { data: network } = useQuery({
    queryKey: ["graph", "network", criminalId],
    queryFn:  () => graphApi.network(criminalId),
    enabled:  activeTab === "network",
    staleTime: STALE_TIME.graph,
  });

  // AI Criminal Brief query
  const { data: aiBrief, isLoading: aiLoading, refetch: fetchAiBrief } = useQuery({
    queryKey: ["assistant", "criminal-summary", criminalId],
    queryFn:  () => assistantApi.criminalSummary(criminalId),
    enabled:  false,
    staleTime: STALE_TIME.assistant,
  });

  if (isLoading) return <LoadingSkeleton variant="detail" />;
  if (!criminal) {
    return (
      <div className="p-12 text-center">
        <AlertTriangle size={40} className="text-[#f85149] mx-auto mb-3" />
        <p className="text-[16px] font-bold text-[#e6edf3]">Offender Profile Not Found</p>
        <Link href="/criminals" className="text-[13px] text-[#58a6ff] hover:underline mt-2 inline-block">
          ← Back to Criminal Intelligence Database
        </Link>
      </div>
    );
  }

  return (
    <div className="p-6 flex flex-col gap-6 max-w-6xl">
      {/* Back button & AI Action Header */}
      <div className="flex items-center justify-between">
        <Link href="/criminals" className="flex items-center gap-1.5 text-[13px] text-[#8b949e] hover:text-[#e6edf3]">
          <ArrowLeft size={14} /> Back to Offender Database
        </Link>

        <button
          onClick={() => fetchAiBrief()}
          disabled={aiLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[rgba(188,140,255,0.15)] border border-[rgba(188,140,255,0.4)] text-[#bc8cff] text-[12px] font-semibold rounded hover:bg-[rgba(188,140,255,0.2)]"
        >
          <Bot size={13} />
          {aiLoading ? "Generating Brief…" : "Generate AI Profile Brief"}
        </button>
      </div>

      {/* Profile Dossier Header Card */}
      <div className="pac-card flex items-start gap-5 border-[#30363d]">
        <div className="w-20 h-20 rounded-lg bg-[#0d1117] border border-[#30363d] flex items-center justify-center text-[#58a6ff] flex-shrink-0">
          <User size={36} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-[20px] font-bold text-[#e6edf3]">{criminal.name}</h1>
            {prediction && <RiskBadge level={prediction.risk_level ?? "MODERATE"} />}
            {criminal.is_wanted ? (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#f85149]/15 text-[#f85149] border border-[#f85149]/30">
                WANTED
              </span>
            ) : (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#3fb950]/15 text-[#3fb950] border border-[#3fb950]/30">
                {criminal.is_repeat_offender ? "REPEAT OFFENDER" : "REGISTERED"}
              </span>
            )}
          </div>

          <p className="text-[13px] text-[#8b949e] mt-1 font-mono">
            Aliases: {criminal.aliases?.length ? criminal.aliases.join(", ") : "None registered"}
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 border-t border-[#30363d] mt-4 pt-3 text-[12px]">
            <div>
              <p className="text-[10px] text-[#8b949e] uppercase font-mono">District</p>
              <p className="text-[#e6edf3] font-semibold">{criminal.district || "Unassigned"}</p>
            </div>
            <div>
              <p className="text-[10px] text-[#8b949e] uppercase font-mono">Gang Affiliation</p>
              <p className="text-[#bc8cff] font-mono">{criminal.gang_name || "Independent"}</p>
            </div>
            <div>
              <p className="text-[10px] text-[#8b949e] uppercase font-mono">Previous Cases</p>
              <p className="text-[#58a6ff] font-mono font-semibold">{criminal.previous_cases_count ?? 0} cases</p>
            </div>
            <div>
              <p className="text-[10px] text-[#8b949e] uppercase font-mono">State / Location</p>
              <p className="text-[#e6edf3] font-mono">{criminal.address || criminal.state || "Karnataka"}</p>
            </div>
          </div>
        </div>
      </div>

      {/* AI Briefing Output (if generated) */}
      {aiBrief && (
        <div className="pac-card border-[rgba(188,140,255,0.4)] bg-[rgba(188,140,255,0.04)] flex flex-col gap-4 animate-fade-in">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold text-[#bc8cff] flex items-center gap-2">
              <Bot size={16} /> AI Offender Intelligence Brief
            </h2>
            <SourceChipList sources={aiBrief.sources} />
          </div>
          <p className="text-[13px] text-[#c9d1d9] leading-relaxed">{aiBrief.answer}</p>
          <ConfidenceMeter score={aiBrief.confidence} />
          <RecommendationList items={aiBrief.recommendations} title="Operational Recommendations" />
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex border-b border-[#30363d] gap-2">
        {[
          { key: "overview",    label: "Overview & History", icon: User },
          { key: "behavior",    label: "Behaviour Profile",  icon: Activity },
          { key: "predictions", label: "Predictive Risk",    icon: TrendingUp },
          { key: "network",     label: "Network Graph",      icon: Network },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as typeof activeTab)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-[13px] font-semibold border-b-2 transition-colors",
                active
                  ? "border-[#58a6ff] text-[#58a6ff] bg-[#1f6feb]/10"
                  : "border-transparent text-[#8b949e] hover:text-[#e6edf3]",
              )}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-in">
          <div className="pac-card flex flex-col gap-3">
            <h2 className="text-[14px] font-semibold text-[#e6edf3]">Known Address / Territory</h2>
            {criminal.address ? (
              <p className="text-[13px] text-[#c9d1d9] flex items-center gap-2">
                <MapPin size={13} className="text-[#8b949e]" />
                {criminal.address} ({criminal.district || criminal.state})
              </p>
            ) : (
              <p className="text-[12px] text-[#8b949e]">No address recorded.</p>
            )}
          </div>

          <div className="pac-card flex flex-col gap-3">
            <h2 className="text-[14px] font-semibold text-[#e6edf3]">Risk Overview</h2>
            {prediction ? (
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-[#8b949e]">Recidivism Risk Score</span>
                  <span className="font-mono text-[16px] font-bold text-[#f85149]">
                    {scoreToPercent(prediction.prediction_score)}
                  </span>
                </div>
                <ConfidenceMeter score={prediction.confidence} />
                <EvidenceList items={prediction.evidence.slice(0, 3)} variant="evidence" title="Key Risk Indicators" />
              </div>
            ) : (
              <p className="text-[12px] text-[#8b949e]">Loading risk profile…</p>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Behaviour */}
      {activeTab === "behavior" && (
        <div className="pac-card flex flex-col gap-4 animate-fade-in">
          <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
            <Activity size={16} className="text-[#e98d30]" />
            Behavioral Intelligence Profile
          </h2>
          {behavior ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-3 bg-[#0d1117] rounded border border-[#30363d]">
                <p className="text-[10px] text-[#8b949e] font-mono uppercase">Violence Index</p>
                <p className="text-[20px] font-mono font-bold text-[#f85149]">
                  {scoreToPercent(behavior.violence_index)}
                </p>
              </div>
              <div className="p-3 bg-[#0d1117] rounded border border-[#30363d]">
                <p className="text-[10px] text-[#8b949e] font-mono uppercase">Consistency Score</p>
                <p className="text-[20px] font-mono font-bold text-[#3fb950]">
                  {scoreToPercent(behavior.consistency_score)}
                </p>
              </div>
              <div className="p-3 bg-[#0d1117] rounded border border-[#30363d]">
                <p className="text-[10px] text-[#8b949e] font-mono uppercase">Operating Radius</p>
                <p className="text-[20px] font-mono font-bold text-[#58a6ff]">
                  {behavior.operating_radius_km} km
                </p>
              </div>
            </div>
          ) : (
            <p className="text-[13px] text-[#8b949e] py-6 text-center">Loading behavioral analysis…</p>
          )}
        </div>
      )}

      {/* Tab 3: Predictions */}
      {activeTab === "predictions" && (
        <div className="pac-card flex flex-col gap-4 animate-fade-in">
          <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
            <TrendingUp size={16} className="text-[#f85149]" />
            Predictive Recidivism & Threat Analysis
          </h2>
          {prediction ? (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between p-4 bg-[#0d1117] rounded border border-[#30363d]">
                <div>
                  <p className="text-[11px] text-[#8b949e] font-mono uppercase">Calculated Recidivism Index</p>
                  <p className="text-[24px] font-mono font-bold text-[#f85149]">
                    {scoreToPercent(prediction.prediction_score)}
                  </p>
                </div>
                <RiskBadge level={prediction.risk_level ?? "HIGH"} size="md" />
              </div>

              <EvidenceList items={prediction.evidence} variant="evidence" title="Traceable Evidence Facts" />
              <RecommendationList items={prediction.recommendations} title="Operational Recommendations" />
            </div>
          ) : (
            <p className="text-[13px] text-[#8b949e] py-6 text-center">Loading prediction breakdown…</p>
          )}
        </div>
      )}

      {/* Tab 4: Network */}
      {activeTab === "network" && (
        <div className="pac-card flex flex-col gap-4 animate-fade-in">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
              <Network size={16} className="text-[#3fb950]" />
              Neo4j Criminal Network Topology
            </h2>
            <Link
              href={`/network?entity=${criminalId}`}
              className="text-[12px] text-[#58a6ff] hover:underline flex items-center gap-1"
            >
              Open Full Network Explorer →
            </Link>
          </div>

          {network ? (
            <div className="p-4 bg-[#0d1117] rounded border border-[#30363d] flex flex-col gap-3">
              <div className="flex gap-4 text-[12px]">
                <span>Nodes: <strong className="font-mono text-[#58a6ff]">{network.statistics.node_count}</strong></span>
                <span>Edges: <strong className="font-mono text-[#3fb950]">{network.statistics.edge_count}</strong></span>
              </div>
              <div className="flex flex-wrap gap-2 pt-2">
                {network.nodes.map((n) => (
                  <span
                    key={n.id}
                    className="text-[11px] font-mono px-2 py-1 rounded bg-[#21262d] text-[#e6edf3] border border-[#30363d]"
                  >
                    {n.label} ({n.type})
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-[13px] text-[#8b949e] py-6 text-center">Loading graph network preview…</p>
          )}
        </div>
      )}
    </div>
  );
}
