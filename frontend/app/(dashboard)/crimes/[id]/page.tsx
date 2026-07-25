"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { crimesApi }     from "@/lib/api/crimes.api";
import { similarityApi } from "@/lib/api/similarity.api";
import { assistantApi }  from "@/lib/api/assistant.api";
import { graphApi }      from "@/lib/api/graph.api";
import { LoadingSkeleton }  from "@/components/common/LoadingSkeleton";
import { ConfidenceMeter }  from "@/components/intelligence/ConfidenceMeter";
import { SourceChipList }   from "@/components/intelligence/SourceChip";
import { RecommendationList } from "@/components/intelligence/RecommendationCard";

import { STALE_TIME }       from "@/lib/utils/constants";
import {
  ArrowLeft, Shield, MapPin, Calendar, Clock, User, AlertCircle, Sparkles, Network, Bot, RefreshCw
} from "lucide-react";
import { toast } from "sonner";

export default function CrimeDetailPage() {
  const params = useParams();
  const crimeId = params.id as string;
  const queryClient = useQueryClient();

  // Crime detail query
  const { data: crime, isLoading, refetch } = useQuery({
    queryKey: ["crimes", crimeId],
    queryFn:  () => crimesApi.get(crimeId),
    staleTime: STALE_TIME.crimeDetail,
  });

  // Poll for DNA vector embedding readiness if missing
  const [pollCount, setPollCount] = useState(0);
  useEffect(() => {
    if (!crime || crime.has_dna || pollCount > 6) return;

    const timer = setTimeout(() => {
      refetch();
      setPollCount((c) => c + 1);
    }, 5000);

    return () => clearTimeout(timer);
  }, [crime, pollCount, refetch]);

  // Similarity matches
  const { data: matches, isLoading: matchesLoading } = useQuery({
    queryKey: ["similarity", crimeId],
    queryFn:  () => similarityApi.getForCrime(crimeId),
    enabled:  !!crime,
    staleTime: STALE_TIME.crimes,
  });

  // AI Crime Summary query
  const { data: aiSummary, isLoading: aiLoading, refetch: fetchAiSummary } = useQuery({
    queryKey: ["assistant", "crime-summary", crimeId],
    queryFn:  () => assistantApi.crimeSummary(crimeId),
    enabled:  false,
    staleTime: STALE_TIME.assistant,
  });

  const [synthesizing, setSynthesizing] = useState(false);

  // Sync to graph
  const [syncing, setSyncing] = useState(false);
  const handleGraphSync = async () => {
    setSyncing(true);
    try {
      await graphApi.sync("crime", crimeId);
      toast.success("Crime synced to Neo4j Graph database!");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to sync to graph.";
      toast.error(msg);
    } finally {
      setSyncing(false);
    }
  };

  const handleGenerateAiBrief = async () => {
    setSynthesizing(true);
    toast.info("Synthesizing operational intelligence reframing via local Ollama LLM...");
    try {
      const res = await fetchAiSummary();
      if (res.data) {
        toast.success("AI Intelligence Brief & Reframed Narrative generated!");
      }
    } catch (err: any) {
      const msg = err?.message || "AI Briefing request failed";
      toast.error(msg);
    } finally {
      setSynthesizing(false);
    }
  };

  if (isLoading) return <LoadingSkeleton variant="detail" />;
  if (!crime) {
    return (
      <div className="p-12 text-center">
        <AlertCircle size={40} className="text-[#f85149] mx-auto mb-3" />
        <p className="text-[16px] font-bold text-[#e6edf3]">Crime Record Not Found</p>
        <Link href="/crimes" className="text-[13px] text-[#58a6ff] hover:underline mt-2 inline-block">
          ← Back to Crime Registry
        </Link>
      </div>
    );
  }

  const mo = crime.mo_features;

  return (
    <div className="p-6 flex flex-col gap-6 max-w-6xl">
      {/* Back button & Action Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <Link href="/crimes" className="flex items-center gap-1.5 text-[13px] text-[#8b949e] hover:text-[#e6edf3]">
          <ArrowLeft size={14} /> Back to Crime Registry
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={handleGraphSync}
            disabled={syncing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#21262d] border border-[#30363d] text-[#3fb950] text-[12px] font-semibold rounded hover:bg-[#30363d] cursor-pointer disabled:opacity-50"
          >
            <Network size={13} />
            {syncing ? "Syncing to Neo4j..." : "Sync to Neo4j Graph"}
          </button>
          <button
            onClick={handleGenerateAiBrief}
            disabled={synthesizing || aiLoading}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[rgba(188,140,255,0.15)] border border-[rgba(188,140,255,0.4)] text-[#bc8cff] text-[12px] font-semibold rounded hover:bg-[rgba(188,140,255,0.25)] cursor-pointer disabled:opacity-50"
          >
            <Bot size={13} className={synthesizing || aiLoading ? "animate-spin" : ""} />
            {synthesizing || aiLoading ? "Analyzing Case with AI..." : "Generate AI Brief"}
          </button>
        </div>
      </div>

      {/* Case Header Card */}
      <div className="pac-card flex flex-col gap-4 border-[#58a6ff]/40">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-[20px] font-bold font-mono text-[#58a6ff]">
                {crime.fir_number}
              </h1>
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase ${
                crime.severity === "critical" ? "bg-[#da3633]/20 text-[#f85149] border border-[#f85149]/30" :
                crime.severity === "high"     ? "bg-[#d29922]/20 text-[#d29922] border border-[#d29922]/30" :
                crime.severity === "medium"   ? "bg-[#e3b341]/20 text-[#e3b341]" : "bg-[#238636]/20 text-[#3fb950]"
              }`}>
                {crime.severity} Severity
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-[#21262d] text-[#8b949e] border border-[#30363d] capitalize">
                {crime.status.replace("_", " ")}
              </span>
            </div>
            <p className="text-[13px] text-[#8b949e] mt-1 capitalize font-medium">
              Category: <span className="text-[#e6edf3] font-semibold">{crime.crime_type.replace("_", " ")}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            {crime.has_dna ? (
              <span className="flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-[#238636]/20 text-[#3fb950] border border-[#3fb950]/30 font-semibold">
                <Sparkles size={12} /> Crime DNA Embedded (384d)
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-[#d29922]/20 text-[#d29922] border border-[#d29922]/30 font-semibold animate-pulse">
                <RefreshCw size={12} className="animate-spin" /> Vectorizing DNA...
              </span>
            )}
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-3.5 bg-[#0d1117] rounded border border-[#30363d] text-[12px]">
          <div>
            <p className="text-[10px] text-[#8b949e] font-mono uppercase">District</p>
            <p className="text-[#e6edf3] font-semibold">{crime.district}</p>
          </div>
          <div>
            <p className="text-[10px] text-[#8b949e] font-mono uppercase">Police Station</p>
            <p className="text-[#e6edf3] font-semibold">{crime.police_station}</p>
          </div>
          <div>
            <p className="text-[10px] text-[#8b949e] font-mono uppercase">Occurred Date</p>
            <p className="text-[#e6edf3] font-semibold">
              {new Date(crime.occurred_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
            </p>
          </div>
          <div>
            <p className="text-[10px] text-[#8b949e] font-mono uppercase">Location Address</p>
            <p className="text-[#e6edf3] font-semibold truncate" title={crime.location_address ?? undefined}>
              {crime.location_address || "N/A"}
            </p>

          </div>
        </div>
      </div>

      {/* AI Intelligence Briefing Output (if triggered) */}
      {aiSummary && (
        <div className="pac-card border-[rgba(188,140,255,0.4)] bg-[rgba(188,140,255,0.04)] flex flex-col gap-4 animate-fade-in">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold text-[#bc8cff] flex items-center gap-2">
              <Bot size={16} /> AI Analytical Case Summary & Reframed Brief
            </h2>
            <SourceChipList sources={aiSummary.sources} />
          </div>
          <div className="p-3.5 rounded bg-[#0d1117] border border-[rgba(188,140,255,0.2)]">
            <p className="text-[11px] font-mono uppercase text-[#bc8cff] font-semibold mb-1">
              AI Reframed Operational Narrative
            </p>
            <p className="text-[13px] text-[#e6edf3] leading-relaxed whitespace-pre-wrap">{aiSummary.answer}</p>
          </div>
          <ConfidenceMeter score={aiSummary.confidence} />
          <RecommendationList items={aiSummary.recommendations} title="Operational Recommendations" />
        </div>
      )}

      {/* Main Content Split — MO Narrative + MO Features */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Narrative & MO Text */}
        <div className="pac-card flex flex-col gap-4">
          <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
            <Shield size={16} className="text-[#58a6ff]" />
            Case Narrative & MO Text
          </h2>

          <div className="bg-[#0d1117] p-3.5 rounded border border-[#30363d] flex flex-col gap-1">
            <p className="text-[10px] text-[#8b949e] font-mono uppercase font-semibold">Registered FIR Raw Input</p>
            <p className="text-[13px] text-[#c9d1d9] leading-relaxed font-sans">
              {crime.description || "No description recorded."}
            </p>
          </div>

          {crime.mo_text && (
            <div className="mt-1 pt-3 border-t border-[#30363d]">
              <p className="text-[11px] text-[#bc8cff] font-mono uppercase font-semibold mb-1">
                Full Modus Operandi (MO) Text (Used for Crime DNA Embedding)
              </p>
              <p className="text-[12px] text-[#8b949e] italic leading-relaxed bg-[#0d1117] p-3 rounded border border-[#30363d]">
                &quot;{crime.mo_text}&quot;
              </p>
            </div>
          )}

          {/* AI Reframed Synthesis Section */}
          <div className="mt-1 pt-3 border-t border-[#30363d]">
            <p className="text-[11px] text-[#3fb950] font-mono uppercase font-semibold mb-1 flex items-center gap-1.5">
              <Sparkles size={12} /> AI Reframed Operational Synthesis
            </p>
            {aiSummary ? (
              <p className="text-[12px] text-[#e6edf3] leading-relaxed bg-[#0d1117] p-3 rounded border border-[#3fb950]/30 font-sans whitespace-pre-line">
                {aiSummary.answer}
              </p>
            ) : (
              <div className="bg-[#0d1117] p-3 rounded border border-[#30363d] flex items-center justify-between text-[12px]">
                <span className="text-[#8b949e]">
                  {synthesizing || aiLoading ? "Synthesizing operational intelligence reframing via Ollama Mistral LLM..." : "Click \"Synthesize\" to generate an operational intelligence brief."}
                </span>
                <button
                  onClick={handleGenerateAiBrief}
                  disabled={synthesizing || aiLoading}
                  className="flex items-center gap-1.5 px-3 py-1 bg-[#21262d] hover:bg-[#30363d] text-[#bc8cff] font-semibold text-[11px] rounded border border-[#30363d] cursor-pointer disabled:opacity-50 transition-colors"
                >
                  <Sparkles size={12} className={synthesizing || aiLoading ? "animate-spin" : ""} />
                  {synthesizing || aiLoading ? "Synthesizing..." : "Synthesize"}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Structured MO Features */}
        <div className="pac-card flex flex-col gap-3">
          <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
            <Shield size={16} className="text-[#d29922]" />
            Rule-Extracted MO Features
          </h2>

          {mo ? (
            <div className="grid grid-cols-2 gap-3 text-[12px]">
              <div className="p-2.5 rounded bg-[#0d1117] border border-[#30363d]">
                <p className="text-[10px] text-[#8b949e] font-mono uppercase">Crime Method</p>
                <p className="text-[#e6edf3] font-semibold capitalize">{mo.crime_method || "N/A"}</p>
              </div>
              <div className="p-2.5 rounded bg-[#0d1117] border border-[#30363d]">
                <p className="text-[10px] text-[#8b949e] font-mono uppercase">Entry Method</p>
                <p className="text-[#e6edf3] font-semibold capitalize">{mo.entry_method || "N/A"}</p>
              </div>
              <div className="p-2.5 rounded bg-[#0d1117] border border-[#30363d]">
                <p className="text-[10px] text-[#8b949e] font-mono uppercase">Target Type</p>
                <p className="text-[#e6edf3] font-semibold capitalize">{mo.target_type || "N/A"}</p>
              </div>
              <div className="p-2.5 rounded bg-[#0d1117] border border-[#30363d]">
                <p className="text-[10px] text-[#8b949e] font-mono uppercase">Weapon Used</p>
                <p className="text-[#e6edf3] font-semibold capitalize">{mo.weapon_used || "None"}</p>
              </div>

              {Array.isArray(mo?.modus_operandi_tags) && mo.modus_operandi_tags.length > 0 ? (
                <div className="col-span-2 p-2.5 rounded bg-[#0d1117] border border-[#30363d]">
                  <p className="text-[10px] text-[#8b949e] font-mono uppercase mb-1">MO Tags</p>
                  <div className="flex flex-wrap gap-1">
                    {mo.modus_operandi_tags.map((tag) => (
                      <span key={tag} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#21262d] text-[#58a6ff] border border-[#30363d]">
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="text-[12px] text-[#8b949e] italic p-3 bg-[#0d1117] rounded border border-[#30363d]">
              No structured MO features extracted.
            </p>
          )}
        </div>
      </div>

      {/* Similar Cases Panel (Crime DNA Search) */}
      <div className="pac-card flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
            <Sparkles size={16} className="text-[#58a6ff]" />
            Similar Cases (Crime DNA Vector Match)
          </h2>
          <span className="text-[12px] font-mono text-[#8b949e]">
            {Array.isArray(matches) ? matches.length : 0} matches found
          </span>
        </div>

        {matchesLoading ? (
          <div className="p-6 text-center text-[#8b949e] text-[13px]">
            Searching vector space for matching Modus Operandi...
          </div>
        ) : !Array.isArray(matches) || matches.length === 0 ? (
          <p className="text-[13px] text-[#8b949e] italic p-4 text-center bg-[#0d1117] rounded border border-[#30363d]">
            No similar crimes found above confidence threshold.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {matches.map((match) => (

              <div key={match.crime_id} className="p-3 bg-[#0d1117] rounded border border-[#30363d] flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-[13px] font-bold font-mono text-[#58a6ff]">{match.fir_number}</span>
                  <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-[#238636]/20 text-[#3fb950]">
                    {(match.similarity_score * 100).toFixed(1)}% Match
                  </span>
                </div>
                <p className="text-[12px] text-[#c9d1d9] line-clamp-2">{match.mo_text}</p>
                <div className="flex items-center justify-between text-[11px] text-[#8b949e] pt-2 border-t border-[#21262d]">
                  <span>{match.district}</span>
                  <Link href={`/crimes/${match.crime_id}`} className="text-[#58a6ff] hover:underline font-semibold">
                    View Case →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
