"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery }  from "@tanstack/react-query";
import { geoApi }         from "@/lib/api/geo.api";
import { assistantApi }   from "@/lib/api/assistant.api";
import { IntelCard }           from "@/components/intelligence/IntelCard";
import { ConfidenceMeter }     from "@/components/intelligence/ConfidenceMeter";
import { RecommendationList }  from "@/components/intelligence/RecommendationCard";
import { SourceChipList }      from "@/components/intelligence/SourceChip";
import { LoadingSkeleton }     from "@/components/common/LoadingSkeleton";
import { KARNATAKA_DISTRICTS, CRIME_TYPE_LABELS, STALE_TIME } from "@/lib/utils/constants";
import { Map, Filter, RefreshCw, Bot, Layers, AlertTriangle, ChevronRight } from "lucide-react";
import type { HotspotResponse } from "@/types/api.types";

export default function GeoIntelligencePage() {
  const [district, setDistrict]     = useState<string>("");
  const [eps, setEps]               = useState<number>(1000);
  const [minSamples, setMinSamples] = useState<number>(5);
  const [selectedHotspot, setSelectedHotspot] = useState<HotspotResponse | null>(null);

  // Fetch DBSCAN hotspots
  const { data: hotspots, isLoading, refetch } = useQuery({
    queryKey:  ["geo", "hotspots", { district, eps, minSamples }],
    queryFn:   () =>
      geoApi.hotspots({
        district:    district || undefined,
        eps,
        min_samples: minSamples,
      }),
    staleTime: STALE_TIME.hotspots,
  });

  // Fetch Geo Stats
  const { data: stats } = useQuery({
    queryKey:  ["geo", "statistics", { district, eps, minSamples }],
    queryFn:   () =>
      geoApi.statistics({
        district:    district || undefined,
        eps,
        min_samples: minSamples,
      }),
    staleTime: STALE_TIME.hotspots,
  });

  // Patrol briefing on selected district
  const { data: briefing, isLoading: briefingLoading, refetch: fetchBriefing } = useQuery({
    queryKey:  ["assistant", "patrol", district],
    queryFn:   () => assistantApi.patrolBriefing(district),
    enabled:   false,
    staleTime: STALE_TIME.assistant,
  });

  return (
    <div className="p-6 flex flex-col gap-6 max-w-[1400px] h-[calc(100vh-56px)] overflow-hidden">
      {/* Page Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-[18px] font-bold text-[#e6edf3] flex items-center gap-2">
            <Map size={20} className="text-[#d29922]" />
            Geo Intelligence & Spatial Hotspot Engine
          </h1>
          <p className="text-[13px] text-[#8b949e] mt-0.5">
            PostGIS DBSCAN clustering & spatial crime density maps for patrol deployment
          </p>
        </div>

        {district && (
          <button
            onClick={() => fetchBriefing()}
            disabled={briefingLoading}
            className="flex items-center gap-2 px-4 py-2 bg-[rgba(188,140,255,0.15)] border border-[rgba(188,140,255,0.4)] text-[#bc8cff] text-[13px] font-semibold rounded hover:bg-[rgba(188,140,255,0.2)] transition-colors"
          >
            <Bot size={14} />
            {briefingLoading ? "Generating Patrol Brief…" : `Get ${district} Patrol Brief`}
          </button>
        )}
      </div>

      {/* Main Split Screen */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0 overflow-hidden">
        {/* Left 2 Cols: Interactive Spatial Map Canvas */}
        <div className="lg:col-span-2 pac-card flex flex-col gap-3 p-0 overflow-hidden relative border-[#30363d]">
          {/* Map Controls Header */}
          <div className="flex items-center justify-between p-3 bg-[#0d1117] border-b border-[#30363d] z-10 flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <select
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="bg-[#161b22] border border-[#30363d] rounded text-[12px] text-[#e6edf3] px-3 py-1 focus:outline-none focus:border-[#58a6ff]"
              >
                <option value="">All Karnataka Districts</option>
                {KARNATAKA_DISTRICTS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>

              <div className="flex items-center gap-2 text-[12px] text-[#8b949e]">
                <span>Radius (eps):</span>
                <input
                  type="number"
                  value={eps}
                  onChange={(e) => setEps(Number(e.target.value))}
                  className="w-16 bg-[#161b22] border border-[#30363d] rounded text-[11px] font-mono text-[#e6edf3] px-2 py-0.5"
                />
                <span>m</span>
              </div>

              <div className="flex items-center gap-2 text-[12px] text-[#8b949e]">
                <span>Min Samples:</span>
                <input
                  type="number"
                  value={minSamples}
                  onChange={(e) => setMinSamples(Number(e.target.value))}
                  className="w-14 bg-[#161b22] border border-[#30363d] rounded text-[11px] font-mono text-[#e6edf3] px-2 py-0.5"
                />
              </div>
            </div>

            <button
              onClick={() => refetch()}
              className="p-1.5 rounded bg-[#21262d] border border-[#30363d] text-[#8b949e] hover:text-[#e6edf3]"
              title="Recalculate DBSCAN clusters"
            >
              <RefreshCw size={13} />
            </button>
          </div>

          {/* Map Container Viewport */}
          <div className="flex-1 bg-[#0d1117] relative flex items-center justify-center p-4">
            {isLoading ? (
              <LoadingSkeleton variant="map" />
            ) : (
              <div className="w-full h-full border border-[#30363d] rounded relative overflow-hidden flex flex-col justify-between p-4 bg-[#080b0f] text-[#8b949e]">
                {/* Map Mock Spatial Viewport */}
                <div className="flex items-center justify-between text-[11px] font-mono text-[#484f58]">
                  <span>LAT: 15.3173° N | LNG: 75.7139° E</span>
                  <span>OPENSTREETMAP VECTOR ENGINE</span>
                </div>

                {/* Hotspot Visual Markers Container */}
                <div className="my-auto grid grid-cols-2 md:grid-cols-3 gap-3">
                  {hotspots?.slice(0, 6).map((h) => (
                    <div
                      key={h.cluster_id}
                      onClick={() => setSelectedHotspot(h)}
                      className="p-3 rounded bg-[#161b22] border border-[#30363d] hover:border-[#d29922] cursor-pointer transition-colors flex flex-col gap-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-mono font-bold text-[#d29922]">
                          Cluster #{h.cluster_id}
                        </span>
                        <span className="text-[10px] font-mono bg-[rgba(210,153,34,0.15)] text-[#d29922] px-1.5 py-0.5 rounded border border-[rgba(210,153,34,0.3)]">
                          {h.crime_count} FIRs
                        </span>
                      </div>
                      <p className="text-[12px] font-semibold text-[#e6edf3]">
                        {CRIME_TYPE_LABELS[h.dominant_type] ?? h.dominant_type}
                      </p>
                      <p className="text-[11px] text-[#8b949e] font-mono">
                        Radius: {Math.round(h.radius_m)}m
                      </p>
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-[#3fb950]">● DBSCAN CLUSTERING ACTIVE</span>
                  <span>{hotspots?.length ?? 0} Clusters Rendered</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Intelligence Stats & Selected Hotspot Inspector */}
        <div className="lg:col-span-1 flex flex-col gap-4 overflow-y-auto pr-1">
          {/* Spatial Statistics Summary */}
          <div className="pac-card flex flex-col gap-3">
            <h2 className="text-[13px] font-semibold text-[#e6edf3]">Spatial Density Metrics</h2>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-2.5 bg-[#0d1117] rounded border border-[#30363d]">
                <p className="text-[10px] text-[#8b949e] font-mono uppercase">Total Clusters</p>
                <p className="text-[18px] font-mono font-bold text-[#d29922]">{stats?.total_clusters ?? "—"}</p>
              </div>
              <div className="p-2.5 bg-[#0d1117] rounded border border-[#30363d]">
                <p className="text-[10px] text-[#8b949e] font-mono uppercase">Avg Cluster Size</p>
                <p className="text-[18px] font-mono font-bold text-[#58a6ff]">{stats?.avg_cluster_size ? Math.round(stats.avg_cluster_size) : "—"}</p>
              </div>
            </div>
          </div>

          {/* AI Patrol Briefing Box (if triggered) */}
          {briefing && (
            <div className="pac-card border-[rgba(188,140,255,0.4)] bg-[rgba(188,140,255,0.04)] flex flex-col gap-3 animate-fade-in">
              <h2 className="text-[13px] font-semibold text-[#bc8cff] flex items-center gap-2">
                <Bot size={15} /> District Patrol Recommendations
              </h2>
              <p className="text-[12px] text-[#c9d1d9] leading-relaxed">{briefing.answer}</p>
              <ConfidenceMeter score={briefing.confidence} />
              <RecommendationList items={briefing.recommendations} />
            </div>
          )}

          {/* Hotspot Inspector */}
          {selectedHotspot ? (
            <div className="pac-card flex flex-col gap-3 border-[#d29922]/40">
              <div className="flex items-center justify-between">
                <h2 className="text-[13px] font-semibold text-[#d29922]">
                  Cluster #{selectedHotspot.cluster_id} Detail
                </h2>
                <button onClick={() => setSelectedHotspot(null)} className="text-[11px] text-[#8b949e] hover:text-[#e6edf3]">
                  Close
                </button>
              </div>
              <div className="text-[12px] text-[#c9d1d9] flex flex-col gap-1">
                <p>Dominant Type: <strong className="text-[#e6edf3]">{CRIME_TYPE_LABELS[selectedHotspot.dominant_type]}</strong></p>
                <p>Crime Count: <strong className="font-mono text-[#58a6ff]">{selectedHotspot.crime_count} FIRs</strong></p>
                <p>Radius: <strong className="font-mono text-[#8b949e]">{Math.round(selectedHotspot.radius_m)} meters</strong></p>
              </div>
            </div>
          ) : (
            <div className="pac-card text-center py-8 text-[12px] text-[#8b949e]">
              Click a cluster marker on the map to inspect spatial crime details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
