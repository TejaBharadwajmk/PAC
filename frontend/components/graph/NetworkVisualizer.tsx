"use client";

import React, { useRef, useEffect, useState, useCallback } from "react";
import {
  ZoomIn, ZoomOut, Maximize2, Play, Pause, Download,
} from "lucide-react";

export interface GraphNodeData {
  id: string;
  label: string;
  type: "criminal" | "crime" | "gang" | "victim" | string;
  risk_level?: "HIGH" | "MEDIUM" | "LOW" | string;
  properties?: Record<string, any>;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  isDragging?: boolean;
}

export interface GraphLinkData {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string;
}

interface NetworkVisualizerProps {
  nodes: GraphNodeData[];
  links: GraphLinkData[];
  selectedNodeId?: string | null;
  onSelectNode: (node: GraphNodeData | null) => void;
  onExpandNode?: (node: GraphNodeData) => void;
}

// ── Color Theme Tokens ────────────────────────────────────────────────────────
const THEME_MAP: Record<string, {
  gradStart: string;
  gradEnd: string;
  stroke: string;
  glow: string;
  text: string;
  iconSymbol: string;
}> = {
  criminal: {
    gradStart: "#ef4444",
    gradEnd: "#991b1b",
    stroke: "#f87171",
    glow: "rgba(239, 68, 68, 0.45)",
    text: "#fee2e2",
    iconSymbol: "👤",
  },
  crime: {
    gradStart: "#3b82f6",
    gradEnd: "#1e3a8a",
    stroke: "#60a5fa",
    glow: "rgba(59, 130, 246, 0.45)",
    text: "#dbeafe",
    iconSymbol: "📄",
  },
  gang: {
    gradStart: "#a855f7",
    gradEnd: "#581c87",
    stroke: "#c084fc",
    glow: "rgba(168, 85, 247, 0.45)",
    text: "#f3e8ff",
    iconSymbol: "👑",
  },
  victim: {
    gradStart: "#10b981",
    gradEnd: "#064e3b",
    stroke: "#34d399",
    glow: "rgba(16, 185, 129, 0.45)",
    text: "#d1fae5",
    iconSymbol: "👁️",
  },
  default: {
    gradStart: "#6b7280",
    gradEnd: "#1f2937",
    stroke: "#9ca3af",
    glow: "rgba(107, 114, 128, 0.45)",
    text: "#f3f4f6",
    iconSymbol: "🔗",
  },
};

export function NetworkVisualizer({
  nodes,
  links,
  selectedNodeId,
  onSelectNode,
  onExpandNode,
}: NetworkVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Simulation & Viewport State
  const [positions, setPositions] = useState<Map<string, { x: number; y: number; vx: number; vy: number }>>(new Map());
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPhysicsRunning, setIsPhysicsRunning] = useState<boolean>(true);
  const [layoutMode, setLayoutMode] = useState<"force" | "radial" | "grid">("force");
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Dragging Refs
  const isPanningRef = useRef<boolean>(false);
  const dragNodeIdRef = useRef<string | null>(null);
  const startMousePosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const pulsePhaseRef = useRef<number>(0);

  // Initialize node positions
  useEffect(() => {
    setPositions((prev) => {
      const next = new Map(prev);
      const radius = Math.min(320, Math.max(160, nodes.length * 28));

      if (layoutMode === "radial") {
        nodes.forEach((node, idx) => {
          const angle = (idx / Math.max(1, nodes.length)) * 2 * Math.PI;
          const r = node.type === "gang" ? radius * 0.3 : node.type === "criminal" ? radius * 0.75 : radius;
          next.set(node.id, {
            x: Math.cos(angle) * r,
            y: Math.sin(angle) * r,
            vx: 0,
            vy: 0,
          });
        });
      } else if (layoutMode === "grid") {
        const cols = Math.ceil(Math.sqrt(nodes.length));
        const spacing = 120;
        nodes.forEach((node, idx) => {
          const row = Math.floor(idx / cols);
          const col = idx % cols;
          next.set(node.id, {
            x: (col - cols / 2) * spacing,
            y: (row - cols / 2) * spacing,
            vx: 0,
            vy: 0,
          });
        });
      } else {
        nodes.forEach((node, idx) => {
          if (!next.has(node.id)) {
            const angle = (idx / Math.max(1, nodes.length)) * 2 * Math.PI;
            next.set(node.id, {
              x: Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
              y: Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
              vx: 0,
              vy: 0,
            });
          }
        });
      }
      return next;
    });
  }, [nodes, layoutMode]);

  // Force-directed Physics loop
  useEffect(() => {
    if (!isPhysicsRunning || layoutMode !== "force") return;

    let animId: number;
    const stepPhysics = () => {
      pulsePhaseRef.current = (pulsePhaseRef.current + 0.05) % (Math.PI * 2);

      setPositions((prev) => {
        const next = new Map(prev);
        const k = 130;
        const damping = 0.82;

        const nodeKeys = Array.from(next.keys());
        for (let i = 0; i < nodeKeys.length; i++) {
          for (let j = i + 1; j < nodeKeys.length; j++) {
            const idA = nodeKeys[i];
            const idB = nodeKeys[j];
            const posA = next.get(idA)!;
            const posB = next.get(idB)!;

            let dx = posB.x - posA.x;
            let dy = posB.y - posA.y;
            let dist = Math.sqrt(dx * dx + dy * dy) || 1;
            if (dist < 350) {
              const force = (k * k) / (dist * dist) * 0.6;
              const fx = (dx / dist) * force;
              const fy = (dy / dist) * force;

              posA.vx -= fx;
              posA.vy -= fy;
              posB.vx += fx;
              posB.vy += fy;
            }
          }
        }

        links.forEach((link) => {
          const posA = next.get(link.source);
          const posB = next.get(link.target);
          if (posA && posB) {
            let dx = posB.x - posA.x;
            let dy = posB.y - posA.y;
            let dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = (dist - k) * 0.035;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            posA.vx += fx;
            posA.vy += fy;
            posB.vx -= fx;
            posB.vy -= fy;
          }
        });

        next.forEach((pos, id) => {
          if (dragNodeIdRef.current === id) return;
          pos.vx *= damping;
          pos.vy *= damping;
          pos.x += pos.vx;
          pos.y += pos.vy;
        });

        return next;
      });

      animId = requestAnimationFrame(stepPhysics);
    };

    animId = requestAnimationFrame(stepPhysics);
    return () => cancelAnimationFrame(animId);
  }, [isPhysicsRunning, links, layoutMode]);

  // Main Canvas Render
  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    ctx.clearRect(0, 0, width, height);

    // ── 0. Draw Tactical Background Grid & Radar Lattice ──────────────
    ctx.save();
    ctx.fillStyle = "#090d14";
    ctx.fillRect(0, 0, width, height);

    // Draw Cyber Grid Lines
    const gridSize = 40 * zoom;
    const offsetX = (width / 2 + pan.x) % gridSize;
    const offsetY = (height / 2 + pan.y) % gridSize;

    ctx.strokeStyle = "rgba(48, 54, 61, 0.25)";
    ctx.lineWidth = 0.5;

    for (let x = offsetX; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = offsetY; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Apply pan & zoom transforms
    ctx.translate(width / 2 + pan.x, height / 2 + pan.y);
    ctx.scale(zoom, zoom);

    // ── 1. Draw Links (Curved Bezier Paths with Flow Particles) ──────
    links.forEach((link) => {
      const sourcePos = positions.get(link.source);
      const targetPos = positions.get(link.target);
      if (!sourcePos || !targetPos) return;

      const isSelected = selectedNodeId === link.source || selectedNodeId === link.target;
      const isHovered = hoveredNodeId === link.source || hoveredNodeId === link.target;

      const midX = (sourcePos.x + targetPos.x) / 2;
      const midY = (sourcePos.y + targetPos.y) / 2;
      const dx = targetPos.x - sourcePos.x;
      const dy = targetPos.y - sourcePos.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const normX = -dy / dist;
      const normY = dx / dist;
      const curvature = Math.min(30, dist * 0.15);
      const controlX = midX + normX * curvature;
      const controlY = midY + normY * curvature;

      ctx.beginPath();
      ctx.moveTo(sourcePos.x, sourcePos.y);
      ctx.quadraticCurveTo(controlX, controlY, targetPos.x, targetPos.y);

      ctx.strokeStyle = isSelected
        ? "#3fb950"
        : isHovered
        ? "#58a6ff"
        : "rgba(48, 54, 61, 0.7)";
      ctx.lineWidth = isSelected ? 2.5 : isHovered ? 2.0 : 1.2;
      ctx.stroke();

      // Flow Micro-Particle along edge
      if (isPhysicsRunning) {
        const t = (pulsePhaseRef.current / (Math.PI * 2) + link.id.length * 0.1) % 1.0;
        const px = (1 - t) * (1 - t) * sourcePos.x + 2 * (1 - t) * t * controlX + t * t * targetPos.x;
        const py = (1 - t) * (1 - t) * sourcePos.y + 2 * (1 - t) * t * controlY + t * t * targetPos.y;

        ctx.beginPath();
        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = isSelected ? "#3fb950" : "#58a6ff";
        ctx.shadowColor = isSelected ? "#3fb950" : "#58a6ff";
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // Link Relation Badge (Pill)
      if (link.type || link.label) {
        const relText = link.type || link.label || "";
        ctx.font = "bold 9px monospace";
        const textWidth = ctx.measureText(relText).width;

        ctx.fillStyle = isSelected ? "rgba(22, 27, 34, 0.9)" : "rgba(13, 17, 23, 0.85)";
        ctx.fillRect(controlX - textWidth / 2 - 4, controlY - 7, textWidth + 8, 14);

        ctx.strokeStyle = isSelected ? "#3fb950" : "#30363d";
        ctx.lineWidth = 1;
        ctx.strokeRect(controlX - textWidth / 2 - 4, controlY - 7, textWidth + 8, 14);

        ctx.fillStyle = isSelected ? "#3fb950" : "#8b949e";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(relText, controlX, controlY);
      }
    });

    // ── 2. Draw Nodes (Gradients, Pulsing Aura, & Badges) ─────────────
    nodes.forEach((node) => {
      const pos = positions.get(node.id);
      if (!pos) return;

      const isSelected = selectedNodeId === node.id;
      const isHovered = hoveredNodeId === node.id;
      const nodeType = (node.type || "default").toLowerCase();
      const theme = THEME_MAP[nodeType] || THEME_MAP.default;
      const radius = nodeType === "gang" ? 26 : 22;

      // Outer Pulsing Glow Halo
      const pulseScale = Math.sin(pulsePhaseRef.current * 2) * 2;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius + (isSelected ? 10 : isHovered ? 8 : 4) + pulseScale, 0, Math.PI * 2);
      ctx.fillStyle = isSelected ? "rgba(63, 185, 80, 0.2)" : isHovered ? theme.glow : "rgba(255, 255, 255, 0.03)";
      ctx.fill();

      if (isSelected || isHovered) {
        ctx.strokeStyle = isSelected ? "#3fb950" : theme.stroke;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Base Radial Gradient Node Body
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      const radGrad = ctx.createRadialGradient(
        pos.x - radius * 0.3,
        pos.y - radius * 0.3,
        2,
        pos.x,
        pos.y,
        radius
      );
      radGrad.addColorStop(0, theme.gradStart);
      radGrad.addColorStop(1, theme.gradEnd);

      ctx.fillStyle = radGrad;
      ctx.shadowColor = theme.glow;
      ctx.shadowBlur = 12;
      ctx.fill();
      ctx.shadowBlur = 0;

      ctx.strokeStyle = isSelected ? "#3fb950" : theme.stroke;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Icon Symbol Inside Node
      ctx.font = "13px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(theme.iconSymbol, pos.x, pos.y);

      // High Risk Warning Badge
      if (node.properties?.risk_level === "HIGH" || node.risk_level === "HIGH") {
        ctx.beginPath();
        ctx.arc(pos.x + radius * 0.75, pos.y - radius * 0.75, 7, 0, Math.PI * 2);
        ctx.fillStyle = "#ef4444";
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.font = "bold 9px sans-serif";
        ctx.fillStyle = "#ffffff";
        ctx.fillText("!", pos.x + radius * 0.75, pos.y - radius * 0.75);
      }

      // Label (Below Node with Background Pill)
      const labelText = node.label || node.id;
      const displayLabel = labelText.length > 16 ? labelText.slice(0, 14) + "…" : labelText;

      ctx.font = "bold 11px system-ui, sans-serif";
      const labelWidth = ctx.measureText(displayLabel).width;

      ctx.fillStyle = "rgba(13, 17, 23, 0.85)";
      ctx.fillRect(pos.x - labelWidth / 2 - 5, pos.y + radius + 6, labelWidth + 10, 16);

      ctx.strokeStyle = isSelected ? "#3fb950" : "rgba(48, 54, 61, 0.6)";
      ctx.lineWidth = 1;
      ctx.strokeRect(pos.x - labelWidth / 2 - 5, pos.y + radius + 6, labelWidth + 10, 16);

      ctx.fillStyle = isSelected ? "#3fb950" : "#e6edf3";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(displayLabel, pos.x, pos.y + radius + 14);
    });

    ctx.restore();
  }, [nodes, links, positions, zoom, pan, selectedNodeId, hoveredNodeId, isPhysicsRunning]);

  useEffect(() => {
    let frameId: number;
    const loop = () => {
      renderCanvas();
      frameId = requestAnimationFrame(loop);
    };
    frameId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frameId);
  }, [renderCanvas]);

  const screenToWorld = useCallback((screenX: number, screenY: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;

    const x = (screenX - rect.left - width / 2 - pan.x) / zoom;
    const y = (screenY - rect.top - height / 2 - pan.y) / zoom;
    return { x, y };
  }, [pan, zoom]);

  const findNodeAt = useCallback((worldX: number, worldY: number) => {
    for (const node of nodes) {
      const pos = positions.get(node.id);
      if (!pos) continue;
      const radius = 28;
      const dx = worldX - pos.x;
      const dy = worldY - pos.y;
      if (dx * dx + dy * dy <= radius * radius) {
        return node;
      }
    }
    return null;
  }, [nodes, positions]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const worldPos = screenToWorld(e.clientX, e.clientY);
    const clickedNode = findNodeAt(worldPos.x, worldPos.y);

    if (clickedNode) {
      dragNodeIdRef.current = clickedNode.id;
      onSelectNode(clickedNode);
    } else {
      isPanningRef.current = true;
      startMousePosRef.current = { x: e.clientX, y: e.clientY };
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const worldPos = screenToWorld(e.clientX, e.clientY);
    const hovered = findNodeAt(worldPos.x, worldPos.y);
    setHoveredNodeId(hovered ? hovered.id : null);

    if (dragNodeIdRef.current) {
      setPositions((prev) => {
        const next = new Map(prev);
        const curr = next.get(dragNodeIdRef.current!);
        if (curr) {
          next.set(dragNodeIdRef.current!, { ...curr, x: worldPos.x, y: worldPos.y, vx: 0, vy: 0 });
        }
        return next;
      });
    } else if (isPanningRef.current) {
      const dx = e.clientX - startMousePosRef.current.x;
      const dy = e.clientY - startMousePosRef.current.y;
      startMousePosRef.current = { x: e.clientX, y: e.clientY };
      setPan((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
    }
  };

  const handleMouseUp = () => {
    dragNodeIdRef.current = null;
    isPanningRef.current = false;
  };

  const handleDoubleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const worldPos = screenToWorld(e.clientX, e.clientY);
    const clickedNode = findNodeAt(worldPos.x, worldPos.y);
    if (clickedNode && onExpandNode) {
      onExpandNode(clickedNode);
    }
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.88;
    setZoom((prev) => Math.min(3.5, Math.max(0.2, prev * zoomFactor)));
  };

  const handleExportPNG = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = `pac_network_topology_${Date.now()}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  };

  return (
    <div className="w-full h-full relative overflow-hidden flex flex-col bg-[#090d14]">
      {/* Interactive Controls Overlay Bar */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 bg-[#0d1117]/90 border border-[#30363d] backdrop-blur-md p-1.5 rounded-lg shadow-xl text-[12px]">
        <button
          onClick={() => setZoom((prev) => Math.min(3.5, prev * 1.2))}
          className="p-1.5 text-[#c9d1d9] hover:text-[#e6edf3] hover:bg-[#21262d] rounded transition-colors"
          title="Zoom In"
        >
          <ZoomIn size={15} />
        </button>
        <button
          onClick={() => setZoom((prev) => Math.max(0.2, prev * 0.8))}
          className="p-1.5 text-[#c9d1d9] hover:text-[#e6edf3] hover:bg-[#21262d] rounded transition-colors"
          title="Zoom Out"
        >
          <ZoomOut size={15} />
        </button>
        <button
          onClick={() => { setZoom(1.0); setPan({ x: 0, y: 0 }); }}
          className="p-1.5 text-[#c9d1d9] hover:text-[#e6edf3] hover:bg-[#21262d] rounded transition-colors"
          title="Reset View"
        >
          <Maximize2 size={15} />
        </button>

        <div className="w-px h-4 bg-[#30363d] my-auto" />

        <button
          onClick={() => setIsPhysicsRunning((prev) => !prev)}
          className={`p-1.5 rounded transition-colors flex items-center gap-1 text-[11px] font-mono ${
            isPhysicsRunning
              ? "bg-[#3fb950]/15 text-[#3fb950] border border-[#3fb950]/30"
              : "text-[#8b949e] hover:bg-[#21262d]"
          }`}
          title="Toggle Physics Engine"
        >
          {isPhysicsRunning ? <Pause size={14} /> : <Play size={14} />}
          <span>{isPhysicsRunning ? "LIVE PHYSICS" : "PAUSED"}</span>
        </button>

        <div className="w-px h-4 bg-[#30363d] my-auto" />

        <div className="flex items-center gap-1 bg-[#161b22] p-0.5 rounded border border-[#30363d] text-[11px] font-mono">
          <button
            onClick={() => setLayoutMode("force")}
            className={`px-2 py-0.5 rounded transition-colors ${
              layoutMode === "force" ? "bg-[#30363d] text-[#58a6ff] font-bold" : "text-[#8b949e] hover:text-[#e6edf3]"
            }`}
          >
            Force
          </button>
          <button
            onClick={() => setLayoutMode("radial")}
            className={`px-2 py-0.5 rounded transition-colors ${
              layoutMode === "radial" ? "bg-[#30363d] text-[#58a6ff] font-bold" : "text-[#8b949e] hover:text-[#e6edf3]"
            }`}
          >
            Radial
          </button>
          <button
            onClick={() => setLayoutMode("grid")}
            className={`px-2 py-0.5 rounded transition-colors ${
              layoutMode === "grid" ? "bg-[#30363d] text-[#58a6ff] font-bold" : "text-[#8b949e] hover:text-[#e6edf3]"
            }`}
          >
            Grid
          </button>
        </div>

        <div className="w-px h-4 bg-[#30363d] my-auto" />

        <button
          onClick={handleExportPNG}
          className="p-1.5 text-[#c9d1d9] hover:text-[#e6edf3] hover:bg-[#21262d] rounded transition-colors"
          title="Export Canvas PNG"
        >
          <Download size={15} />
        </button>
      </div>

      {/* HTML5 Canvas Surface */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onDoubleClick={handleDoubleClick}
        onWheel={handleWheel}
        className="w-full h-full cursor-grab active:cursor-grabbing select-none"
      />

      {/* Legend Overlay Badge Bar */}
      <div className="absolute bottom-3 left-3 z-10 flex items-center gap-4 bg-[#161b22]/90 border border-[#30363d] backdrop-blur-md px-3 py-1.5 rounded-lg text-[11px] font-mono shadow-lg">
        <span className="text-[#8b949e] font-semibold">LEGEND</span>
        <div className="flex items-center gap-1.5 text-[#e6edf3]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#ef4444] shadow-[0_0_8px_#ef4444]" /> Criminal
        </div>
        <div className="flex items-center gap-1.5 text-[#e6edf3]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#3b82f6] shadow-[0_0_8px_#3b82f6]" /> Crime Scene
        </div>
        <div className="flex items-center gap-1.5 text-[#e6edf3]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#a855f7] shadow-[0_0_8px_#a855f7]" /> Gang
        </div>
        <div className="flex items-center gap-1.5 text-[#e6edf3]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#10b981] shadow-[0_0_8px_#10b981]" /> Victim
        </div>
      </div>
    </div>
  );
}

