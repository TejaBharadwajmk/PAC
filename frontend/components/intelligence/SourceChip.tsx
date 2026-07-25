"use client";

import { cn } from "@/lib/utils/cn";
import { INTEL_SOURCE_LABELS } from "@/lib/utils/constants";

const SOURCE_COLOURS: Record<string, string> = {
  "Crime DNA":              "#58a6ff",
  "Hybrid Similarity Engine": "#bc8cff",
  "Behaviour Intelligence": "#e98d30",
  "Predictive Intelligence": "#f85149",
  "Criminal Network Intelligence (Neo4j)": "#3fb950",
  "Geo Intelligence":       "#d29922",
};

interface SourceChipProps {
  source:    string;
  size?:     "sm" | "md";
  className?: string;
}

export function SourceChip({ source, size = "sm", className }: SourceChipProps) {
  const label  = INTEL_SOURCE_LABELS[source] ?? source;
  const colour = SOURCE_COLOURS[source] ?? "#8b949e";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 border rounded-sm font-mono uppercase tracking-wider",
        size === "sm"
          ? "text-[10px] px-1.5 py-0.5"
          : "text-[11px] px-2 py-1",
        className,
      )}
      style={{
        color:           colour,
        borderColor:     `${colour}55`,
        backgroundColor: `${colour}15`,
      }}
    >
      <span
        className="rounded-full"
        style={{ width: 4, height: 4, background: colour, display: "inline-block" }}
      />
      {label}
    </span>
  );
}

// ── Source chip row (multiple) ─────────────────────────────────────────────────
interface SourceChipListProps {
  sources:   string[];
  className?: string;
}

export function SourceChipList({ sources, className }: SourceChipListProps) {
  const safeSources = Array.isArray(sources) ? sources : [];
  if (!safeSources.length) return null;
  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {safeSources.map((s) => (
        <SourceChip key={s} source={s} />
      ))}
    </div>
  );
}

