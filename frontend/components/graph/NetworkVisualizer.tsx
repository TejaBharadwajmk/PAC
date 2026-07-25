"use client";

import React, { useRef, useEffect, useState, useCallback } from "react";
import { ZoomIn, ZoomOut, Maximize2, Play, Pause, RefreshCw, Download } from "lucide-react";

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

const COLOR_MAP: Record<string, { fill: string; stroke: string; text: string }> = {
  criminal: { fill: "#ef4444", stroke: "#dc2626", text: "#ffffff" },
  crime: { fill: "#3b82f6", stroke: "#2563eb", text: "#ffffff" },
  gang: { fill: "#8b5cf6", stroke: "#7c3aed", text: "#ffffff" },
  victim: { fill: "#10b981", stroke: "#059669", text: "#ffffff" },
  default: { fill: "#6b7280", stroke: "#4b5563", text: "#ffffff" },
};

export function NetworkVisualizer({
  nodes,
  links,
  selectedNodeId,
  onSelectNode,
  onExpandNode,
}: NetworkVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Layout simulation state
  const [positions, setPositions] = useState<Map<string, { x: number; y: number; vx: number; vy: number }>>(new Map());
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPhysicsRunning, setIsPhysicsRunning] = useState<boolean>(true);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Dragging state
  const isPanningRef = useRef<boolean>(false);
  const dragNodeIdRef = useRef<string | null>(null);
  const startMousePosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Initialize or update node positions in circle/grid if new
  useEffect(() => {
    setPositions((prev) => {
      const next = new Map(prev);
      const radius = Math.min(300, nodes.length * 25);
      nodes.forEach((node, idx) => {
        if (!next.has(node.id)) {
          const angle = (idx / Math.max(1, nodes.length)) * 2 * Math.PI;
          next.set(node.id, {
            x: Math.cos(angle) * radius + (Math.random() - 0.5) * 50,
            y: Math.sin(angle) * radius + (Math.random() - 0.5) * 50,
            vx: 0,
            vy: 0,
          });
        }
      });
      return next;
    });
  }, [nodes]);

  // Physics simulation loop (ForceAtlas / Spring Embedder)
  useEffect(() => {
    if (!isPhysicsRunning) return;

    let animId: number;
    const stepPhysics = () => {
      setPositions((prev) => {
        const next = new Map(prev);
        const k = 120; // Spring length
        const damping = 0.85;

        // 1. Repulsion between all node pairs
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
            if (dist < 300) {
              const force = (k * k) / (dist * dist) * 0.5;
              const fx = (dx / dist) * force;
              const fy = (dy / dist) * force;

              posA.vx -= fx;
              posA.vy -= fy;
              posB.vx += fx;
              posB.vy += fy;
            }
          }
        }

        // 2. Attraction along links
        links.forEach((link) => {
          const posA = next.get(link.source);
          const posB = next.get(link.target);
          if (posA && posB) {
            let dx = posB.x - posA.x;
            let dy = posB.y - posA.y;
            let dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = (dist - k) * 0.03;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            posA.vx += fx;
            posA.vy += fy;
            posB.vx -= fx;
            posB.vy -= fy;
          }
        });

        // 3. Apply velocity and damping
        next.forEach((pos, id) => {
          if (dragNodeIdRef.current === id) return; // Don't move actively dragged node
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
  }, [isPhysicsRunning, links]);

  // Main Canvas Render Loop
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

    // Clear background
    ctx.clearRect(0, 0, width, height);
    ctx.save();

    // Apply pan & zoom transforms (center of canvas origin)
    ctx.translate(width / 2 + pan.x, height / 2 + pan.y);
    ctx.scale(zoom, zoom);

    // ── 1. Draw Links ───────────────────────────────────────────────
    links.forEach((link) => {
      const sourcePos = positions.get(link.source);
      const targetPos = positions.get(link.target);
      if (!sourcePos || !targetPos) return;

      const isSelected = selectedNodeId === link.source || selectedNodeId === link.target;
      ctx.beginPath();
      ctx.moveTo(sourcePos.x, sourcePos.y);
      ctx.lineTo(targetPos.x, targetPos.y);
      ctx.strokeStyle = isSelected ? "#3fb950" : "#30363d";
      ctx.lineWidth = isSelected ? 2.5 : 1.2;
      ctx.stroke();

      // Render link label
      if (link.type || link.label) {
        const midX = (sourcePos.x + targetPos.x) / 2;
        const midY = (sourcePos.y + targetPos.y) / 2;
        ctx.font = "9px monospace";
        ctx.fillStyle = isSelected ? "#3fb950" : "#6e7681";
        ctx.fillText(link.type || link.label || "", midX + 4, midY - 4);
      }
    });

    // ── 2. Draw Nodes ───────────────────────────────────────────────
    nodes.forEach((node) => {
      const pos = positions.get(node.id);
      if (!pos) return;

      const isSelected = selectedNodeId === node.id;
      const isHovered = hoveredNodeId === node.id;
      const theme = COLOR_MAP[node.type] || COLOR_MAP.default;
      const radius = node.type === "gang" ? 26 : 22;

      // Outer selection / highlight ring
      if (isSelected || isHovered) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius + 6, 0, 2 * Math.PI);
        ctx.fillStyle = isSelected ? "rgba(63, 185, 80, 0.25)" : "rgba(88, 166, 255, 0.2)";
        ctx.fill();
        ctx.strokeStyle = isSelected ? "#3fb950" : "#58a6ff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Base Node Circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = theme.fill;
      ctx.fill();
      ctx.strokeStyle = theme.stroke;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Risk level indicator badge for Criminals
      if (node.properties?.risk_level === "HIGH" || node.risk_level === "HIGH") {
        ctx.beginPath();
        ctx.arc(pos.x + radius * 0.7, pos.y - radius * 0.7, 6, 0, 2 * Math.PI);
        ctx.fillStyle = "#ef4444";
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Node Label (inside & below)
      ctx.font = "bold 11px system-ui, sans-serif";
      ctx.fillStyle = "#e6edf3";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const shortName = node.label.length > 14 ? node.label.slice(0, 12) + "…" : node.label;
      ctx.fillText(shortName, pos.x, pos.y + radius + 14);

      // Node Type label inside circle
      ctx.font = "9px monospace";
      ctx.fillStyle = theme.text;
      ctx.fillText(node.type.slice(0, 4).toUpperCase(), pos.x, pos.y);
    });

    ctx.restore();
  }, [nodes, links, positions, zoom, pan, selectedNodeId, hoveredNodeId]);

  useEffect(() => {
    renderCanvas();
  }, [renderCanvas]);

  // Convert mouse screen coordinates to canvas world coordinates
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

  // Find node under mouse position
  const findNodeAt = useCallback((worldX: number, worldY: number) => {
    for (const node of nodes) {
      const pos = positions.get(node.id);
      if (!pos) continue;
      const radius = 26;
      const dx = worldX - pos.x;
      const dy = worldY - pos.y;
      if (dx * dx + dy * dy <= radius * radius) {
        return node;
      }
    }
    return null;
  }, [nodes, positions]);

  // Mouse event handlers
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
    setZoom((prev) => Math.min(3.0, Math.max(0.2, prev * zoomFactor)));
  };

  const handleExportPNG = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const image = canvas.toDataURL("image/png");
    const link = document.createElement("a");
    link.href = image;
    link.download = `neo4j_network_topology_${Date.now()}.png`;
    link.click();
  };

  return (
    <div ref={containerRef} className="w-full h-full relative overflow-hidden bg-[#080b0f] select-none">
      {/* HTML5 Canvas Viewport */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onDoubleClick={handleDoubleClick}
        onWheel={handleWheel}
        className="w-full h-full cursor-grab active:cursor-grabbing"
      />

      {/* Floating Canvas Controls */}
      <div className="absolute bottom-4 left-4 flex items-center gap-1.5 p-1.5 bg-[#0d1117]/90 border border-[#30363d] rounded-lg shadow-xl backdrop-blur-md">
        <button
          onClick={() => setZoom((z) => Math.min(3.0, z * 1.2))}
          title="Zoom In"
          className="p-1.5 text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] rounded transition-colors"
        >
          <ZoomIn size={16} />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(0.2, z * 0.8))}
          title="Zoom Out"
          className="p-1.5 text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] rounded transition-colors"
        >
          <ZoomOut size={16} />
        </button>
        <button
          onClick={() => { setZoom(1.0); setPan({ x: 0, y: 0 }); }}
          title="Reset View"
          className="p-1.5 text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] rounded transition-colors"
        >
          <Maximize2 size={16} />
        </button>
        <div className="w-[1px] h-4 bg-[#30363d] mx-0.5" />
        <button
          onClick={() => setIsPhysicsRunning((p) => !p)}
          title={isPhysicsRunning ? "Pause Physics Simulation" : "Run Physics Simulation"}
          className={`p-1.5 rounded transition-colors ${isPhysicsRunning ? "text-[#3fb950] bg-[rgba(63,185,80,0.15)]" : "text-[#8b949e] hover:text-[#e6edf3]"}`}
        >
          {isPhysicsRunning ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <button
          onClick={handleExportPNG}
          title="Export Canvas PNG"
          className="p-1.5 text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] rounded transition-colors"
        >
          <Download size={16} />
        </button>
      </div>

      {/* Legend Overlay */}
      <div className="absolute top-4 left-4 p-2.5 bg-[#0d1117]/85 border border-[#30363d] rounded-lg shadow-lg text-[11px] font-mono flex flex-col gap-1.5 backdrop-blur-md">
        <span className="text-[#8b949e] font-semibold uppercase text-[10px] tracking-wider mb-0.5">Legend</span>
        <div className="flex items-center gap-2 text-[#e6edf3]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#ef4444]" /> Criminal
        </div>
        <div className="flex items-center gap-2 text-[#e6edf3]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#3b82f6]" /> Crime Scene
        </div>
        <div className="flex items-center gap-2 text-[#e6edf3]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#8b5cf6]" /> Gang
        </div>
        <div className="flex items-center gap-2 text-[#e6edf3]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#10b981]" /> Victim
        </div>
      </div>
    </div>
  );
}
