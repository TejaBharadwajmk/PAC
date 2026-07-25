"use client";

import { cn } from "@/lib/utils/cn";
import type { RiskLevel } from "@/types/api.types";
import { scoreToRiskLevel, riskLevelToHex } from "@/lib/utils/riskLevel";

interface RiskBadgeProps {
  /** Pass a RiskLevel string OR a 0.0–1.0 numeric score */
  level?: RiskLevel | string;
  score?: number;
  size?: "sm" | "md";
  className?: string;
}

const LABELS: Record<string, string> = {
  CRITICAL: "CRITICAL",
  HIGH:     "HIGH",
  MODERATE: "MODERATE",
  LOW:      "LOW",
};

const BG_CLASSES: Record<string, string> = {
  CRITICAL: "bg-[rgba(248,81,73,0.15)] border-[rgba(248,81,73,0.5)] text-[#f85149]",
  HIGH:     "bg-[rgba(233,141,48,0.15)] border-[rgba(233,141,48,0.5)] text-[#e98d30]",
  MODERATE: "bg-[rgba(210,153,34,0.15)] border-[rgba(210,153,34,0.5)] text-[#d29922]",
  LOW:      "bg-[rgba(63,185,80,0.15)] border-[rgba(63,185,80,0.5)] text-[#3fb950]",
};

export function RiskBadge({ level, score, size = "md", className }: RiskBadgeProps) {
  const resolvedLevel: string =
    level
      ? level.toUpperCase()
      : score !== undefined
      ? scoreToRiskLevel(score)
      : "LOW";

  const colourClass = BG_CLASSES[resolvedLevel] ?? BG_CLASSES.LOW;
  const label       = LABELS[resolvedLevel] ?? resolvedLevel;
  const dotColour   = riskLevelToHex(resolvedLevel);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 border rounded-sm font-mono font-semibold tracking-wider uppercase",
        size === "sm"
          ? "text-[10px] px-1.5 py-0.5"
          : "text-[11px] px-2 py-1",
        colourClass,
        className,
      )}
    >
      <span
        className="inline-block rounded-full"
        style={{ width: size === "sm" ? 5 : 6, height: size === "sm" ? 5 : 6, background: dotColour }}
      />
      {label}
    </span>
  );
}
