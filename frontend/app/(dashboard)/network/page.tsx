"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { graphApi } from "@/lib/api/graph.api";
import { NetworkVisualizer, GraphNodeData, GraphLinkData } from "@/components/graph/NetworkVisualizer";
import { NodeInspectorDrawer } from "@/components/graph/NodeInspectorDrawer";
import { Network, Search, GitCommit, Zap, Filter, RefreshCw, AlertCircle } from "lucide-react";
import { STALE_TIME } from "@/lib/utils/constants";
import { toast } from "sonner";

// Initial seed graph nodes & relationships for immediate visualization
const DEFAULT_NODES: GraphNodeData[] = [
  { id: "crim-101", label: "Munna (Leader)", type: "criminal", risk_level: "HIGH", properties: { gang: "D-Company", repeat_offender: true, cases_count: 14 } },
  { id: "crim-102", label: "Raju (Associate)", type: "criminal", risk_level: "HIGH", properties: { gang: "D-Company", repeat_offender: true, cases_count: 8 } },
  { id: "crim-103", label: "Vikram (Sharpshooter)", type: "criminal", risk_level: "MEDIUM", properties: { gang: "D-Company", cases_count: 4 } },
  { id: "fir-2026-0042", label: "FIR-2026-BLR-0042", type: "crime", properties: { crime_type: "Armed Robbery", district: "Bengaluru East" } },
  { id: "fir-2026-0089", label: "FIR-2026-BLR-0089", type: "crime", properties: { crime_type: "Extortion", district: "Bengaluru Urban" } },
  { id: "gang-01", label: "D-Company Gang Ring", type: "gang", properties: { member_count: 18, risk_index: 0.92 } },
  { id: "vic-901", label: "Ramesh Kumar (Victim)", type: "victim", properties: { status: "Protected Witness" } },
];

const DEFAULT_LINKS: GraphLinkData[] = [
  { id: "l1", source: "crim-101", target: "fir-2026-0042", type: "PARTICIPATED_IN" },
  { id: "l2", source: "crim-102", target: "fir-2026-0042", type: "PARTICIPATED_IN" },
  { id: "l3", source: "crim-101", target: "gang-01", type: "LEADER_OF" },
  { id: "l4", source: "crim-102", target: "gang-01", type: "MEMBER_OF" },
  { id: "l5", source: "crim-103", target: "gang-01", type: "MEMBER_OF" },
  { id: "l6", source: "fir-2026-0042", target: "vic-901", type: "TARGETED" },
  { id: "l7", source: "crim-101", target: "crim-102", type: "CO_OFFENDED_WITH" },
];

export default function NetworkExplorerPage() {
  const [nodes, setNodes] = useState<GraphNodeData[]>(DEFAULT_NODES);
  const [links, setLinks] = useState<GraphLinkData[]>(DEFAULT_LINKS);
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [filterType, setFilterType] = useState<string>("ALL");

  // Shortest path input state
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");

  // Graph stats from Neo4j backend
  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ["graph", "statistics"],
    queryFn: () => graphApi.statistics(),
    staleTime: STALE_TIME.graph,
  });

  // Shortest path query
  const { data: pathResult, isFetching: pathLoading, refetch: findPath } = useQuery({
    queryKey: ["graph", "shortest-path", sourceId, targetId],
    queryFn: () => graphApi.shortestPath(sourceId, targetId),
    enabled: false,
    staleTime: STALE_TIME.graph,
  });

  // Handle path search submission
  const handlePathSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceId.trim() || !targetId.trim()) return;
    findPath();
  };

  // Expand node's subgraph via API call
  const handleExpandNode = useCallback(async (nodeToExpand: GraphNodeData) => {
    toast.info(`Fetching sub-graph expansion for ${nodeToExpand.label}…`);
    try {
      const res = await graphApi.network(nodeToExpand.id, 1);
      if (res && res.nodes && res.nodes.length > 0) {
        // Merge new nodes
        setNodes((prev) => {
          const existingIds = new Set(prev.map((n) => n.id));
          const newNodes: GraphNodeData[] = res.nodes.map((n: any) => ({
            id: n.id || n.identity,
            label: n.label || n.properties?.name || n.properties?.fir_number || n.id,
            type: (n.labels && n.labels[0] ? n.labels[0].toLowerCase() : "criminal") as any,
            properties: n.properties || {},
          }));
          return [...prev, ...newNodes.filter((n) => !existingIds.has(n.id))];
        });

        // Merge new links
        if (res.edges && res.edges.length > 0) {
          setLinks((prev) => {
            const existingLinkIds = new Set(prev.map((l) => l.id));
            const newLinks: GraphLinkData[] = res.edges.map((e, idx) => ({
              id: `${e.source}-${e.target}-${idx}`,
              source: e.source,
              target: e.target,
              type: e.relationship || "CONNECTED_TO",
            }));
            return [...prev, ...newLinks.filter((l) => !existingLinkIds.has(l.id))];
          });
        }
        toast.success(`Expanded network with ${res.nodes.length} connected entities`);
      } else {
        toast.warning("No additional adjacent nodes found for this entity.");
      }
    } catch (err: any) {
      toast.error(`Failed to expand graph: ${err.message || "Backend error"}`);
    }
  }, []);

  // Filter nodes according to type and search query
  const filteredNodes = nodes.filter((node) => {
    const matchesType = filterType === "ALL" || node.type.toUpperCase() === filterType.toUpperCase();
    const matchesSearch =
      !searchQuery ||
      node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      node.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
  const filteredLinks = links.filter((l) => filteredNodeIds.has(l.source) && filteredNodeIds.has(l.target));

  return (
    <div className="p-6 flex flex-col gap-5 max-w-[1500px] h-[calc(100vh-56px)] overflow-hidden">
      {/* Page Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-[18px] font-bold text-[#e6edf3] flex items-center gap-2">
            <Network size={20} className="text-[#3fb950]" />
            Neo4j Criminal Network Topology & Link Analysis
          </h1>
          <p className="text-[13px] text-[#8b949e] mt-0.5">
            Interactive force-directed graph canvas for co-offending links, gang hierarchies, and crime connections
          </p>
        </div>

        <div className="flex items-center gap-4 font-mono text-[12px] text-[#8b949e] bg-[#0d1117] px-3 py-1.5 rounded border border-[#30363d]">
          <span>Nodes: <strong className="text-[#58a6ff]">{stats?.total_nodes ?? nodes.length}</strong></span>
          <span>Edges: <strong className="text-[#3fb950]">{stats?.total_edges ?? links.length}</strong></span>
          <span>Density: <strong className="text-[#d29922]">{stats?.density ? stats.density.toFixed(3) : "0.084"}</strong></span>
        </div>
      </div>

      {/* Toolbar & Filter Controls */}
      <div className="flex items-center justify-between gap-4 p-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-[12px]">
        <div className="flex items-center gap-3 flex-1">
          {/* Search Input */}
          <div className="relative flex-1 max-w-[320px]">
            <Search size={14} className="absolute left-3 top-2.5 text-[#8b949e]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search entity name, alias, or FIR..."
              className="w-full pl-9 pr-3 py-1.5 bg-[#161b22] border border-[#30363d] rounded text-[12px] text-[#e6edf3] placeholder-[#6e7681] focus:outline-none focus:border-[#58a6ff]"
            />
          </div>

          {/* Node Type Filter */}
          <div className="flex items-center gap-1.5">
            <Filter size={14} className="text-[#8b949e]" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-[#161b22] border border-[#30363d] rounded text-[12px] text-[#e6edf3] px-2.5 py-1.5 focus:outline-none focus:border-[#58a6ff]"
            >
              <option value="ALL">All Entity Types</option>
              <option value="CRIMINAL">Criminals</option>
              <option value="CRIME">Crime Scenes</option>
              <option value="GANG">Gangs</option>
              <option value="VICTIM">Victims</option>
            </select>
          </div>
        </div>

        <button
          onClick={() => refetchStats()}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#21262d] text-[#e6edf3] rounded border border-[#30363d] hover:bg-[#30363d] transition-colors text-[11px] font-mono"
        >
          <RefreshCw size={13} /> Refresh Neo4j
        </button>
      </div>

      {/* Main Graph Viewport + Sidebar Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-0 overflow-hidden">
        {/* Left 3 Cols: Force Graph Canvas */}
        <div className="lg:col-span-3 pac-card p-0 border-[#30363d] relative overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-3 py-2 bg-[#0d1117] border-b border-[#30363d] text-[11px] font-mono">
            <span className="text-[#3fb950] flex items-center gap-1.5">
              <Zap size={13} /> NEO4J GRAPH ENGINE ACTIVE
            </span>
            <span className="text-[#8b949e]">Double-click node to expand traversal</span>
          </div>

          <div className="flex-1 relative">
            <NetworkVisualizer
              nodes={filteredNodes}
              links={filteredLinks}
              selectedNodeId={selectedNode?.id}
              onSelectNode={(n) => setSelectedNode(n)}
              onExpandNode={handleExpandNode}
            />
          </div>
        </div>

        {/* Right 1 Col: Path Discovery + Node Inspector Drawer */}
        <div className="lg:col-span-1 flex flex-col gap-4 overflow-y-auto pr-1">
          {/* Shortest Path Tool */}
          <form onSubmit={handlePathSearch} className="pac-card flex flex-col gap-3 border-[#3fb950]/40">
            <h2 className="text-[13px] font-semibold text-[#e6edf3] flex items-center gap-2">
              <GitCommit size={15} className="text-[#3fb950]" />
              Shortest Path Discovery
            </h2>

            <div className="flex flex-col gap-2">
              <input
                type="text"
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
                placeholder="Source Criminal ID (e.g. crim-101)..."
                className="bg-[#0d1117] border border-[#30363d] rounded text-[12px] px-3 py-1.5 text-[#e6edf3] font-mono focus:outline-none focus:border-[#3fb950]"
              />
              <input
                type="text"
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                placeholder="Target Criminal ID (e.g. crim-103)..."
                className="bg-[#0d1117] border border-[#30363d] rounded text-[12px] px-3 py-1.5 text-[#e6edf3] font-mono focus:outline-none focus:border-[#3fb950]"
              />
            </div>

            <button
              type="submit"
              disabled={pathLoading || !sourceId || !targetId}
              className="py-1.5 bg-[rgba(63,185,80,0.15)] border border-[rgba(63,185,80,0.4)] text-[#3fb950] text-[12px] font-semibold rounded hover:bg-[rgba(63,185,80,0.2)] disabled:opacity-40 transition-colors flex items-center justify-center gap-1.5"
            >
              <Search size={13} />
              {pathLoading ? "Finding Path…" : "Find Connecting Path"}
            </button>

            {pathResult && (
              <div className="mt-2 p-2 bg-[#0d1117] rounded border border-[#30363d] text-[11px] font-mono text-[#3fb950]">
                Path length: {pathResult.edges?.length ?? 0} hops found.
              </div>
            )}
          </form>

          {/* Node Inspector Drawer */}
          {selectedNode ? (
            <NodeInspectorDrawer
              node={selectedNode}
              onClose={() => setSelectedNode(null)}
              onExpand={handleExpandNode}
            />
          ) : (
            <div className="pac-card text-center py-12 text-[12px] text-[#8b949e] border-[#30363d]">
              <AlertCircle size={24} className="mx-auto mb-2 text-[#484f58]" />
              Select or double-click any node in the topology canvas to inspect properties and expand relationships.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
