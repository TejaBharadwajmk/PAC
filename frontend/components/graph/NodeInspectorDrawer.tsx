"use client";

import React from "react";
import { GraphNodeData } from "./NetworkVisualizer";
import { X, ExternalLink, ShieldAlert, GitFork, User, FileText, Users, Eye } from "lucide-react";

interface NodeInspectorDrawerProps {
  node: GraphNodeData | null;
  onClose: () => void;
  onExpand: (node: GraphNodeData) => void;
}

export function NodeInspectorDrawer({ node, onClose, onExpand }: NodeInspectorDrawerProps) {
  if (!node) return null;

  const getIcon = () => {
    switch (node.type) {
      case "criminal":
        return <User className="text-[#ef4444]" size={18} />;
      case "crime":
        return <FileText className="text-[#3b82f6]" size={18} />;
      case "gang":
        return <Users className="text-[#8b5cf6]" size={18} />;
      case "victim":
        return <Eye className="text-[#10b981]" size={18} />;
      default:
        return <GitFork className="text-[#8b949e]" size={18} />;
    }
  };

  const getTypeBadgeColor = () => {
    switch (node.type) {
      case "criminal":
        return "bg-red-500/15 border-red-500/40 text-red-400";
      case "crime":
        return "bg-blue-500/15 border-blue-500/40 text-blue-400";
      case "gang":
        return "bg-purple-500/15 border-purple-500/40 text-purple-400";
      case "victim":
        return "bg-emerald-500/15 border-emerald-500/40 text-emerald-400";
      default:
        return "bg-gray-500/15 border-gray-500/40 text-gray-400";
    }
  };

  return (
    <div className="pac-card flex flex-col gap-4 border-[#30363d] bg-[#0d1117]/95 shadow-2xl relative overflow-hidden">
      {/* Drawer Header */}
      <div className="flex items-center justify-between border-b border-[#30363d] pb-3">
        <div className="flex items-center gap-2">
          {getIcon()}
          <div>
            <h3 className="text-[14px] font-bold text-[#e6edf3] line-clamp-1">{node.label}</h3>
            <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border inline-block mt-0.5 ${getTypeBadgeColor()}`}>
              {node.type}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] rounded transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* Property Details Grid */}
      <div className="flex flex-col gap-2 text-[12px] text-[#c9d1d9] font-mono">
        <div className="flex justify-between py-1 border-b border-[#21262d]">
          <span className="text-[#8b949e]">Entity ID:</span>
          <span className="text-[#e6edf3] font-mono truncate max-w-[180px]">{node.id}</span>
        </div>

        {node.properties?.risk_level && (
          <div className="flex justify-between py-1 border-b border-[#21262d]">
            <span className="text-[#8b949e]">Risk Level:</span>
            <span className={`font-bold ${node.properties.risk_level === "HIGH" ? "text-red-400" : "text-amber-400"}`}>
              {node.properties.risk_level}
            </span>
          </div>
        )}

        {node.properties &&
          Object.entries(node.properties)
            .filter(([key]) => !["id", "label", "type", "risk_level"].includes(key))
            .map(([key, val]) => (
              <div key={key} className="flex justify-between py-1 border-b border-[#21262d]">
                <span className="text-[#8b949e] capitalize">{key.replace(/_/g, " ")}:</span>
                <span className="text-[#e6edf3] truncate max-w-[180px]">
                  {typeof val === "object" ? JSON.stringify(val) : String(val)}
                </span>
              </div>
            ))}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col gap-2 pt-2 border-t border-[#30363d]">
        <button
          onClick={() => onExpand(node)}
          className="w-full py-1.5 px-3 bg-[rgba(63,185,80,0.15)] border border-[rgba(63,185,80,0.4)] text-[#3fb950] text-[12px] font-semibold rounded hover:bg-[rgba(63,185,80,0.2)] transition-colors flex items-center justify-center gap-1.5"
        >
          <GitFork size={14} />
          Expand Subgraph Traversal
        </button>
      </div>
    </div>
  );
}
