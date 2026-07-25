"use client";

import { cn } from "@/lib/utils/cn";
import { AlertTriangle } from "lucide-react";

interface RecommendationCardProps {
  text:        string;
  priority?:   "urgent" | "moderate" | "routine";
  index?:      number;
  className?:  string;
}

const PRIORITY_CONFIG = {
  urgent: {
    border: "border-[rgba(248,81,73,0.4)]",
    icon:   "text-[#f85149]",
    badge:  "URGENT",
    badgeClass: "text-[#f85149] bg-[rgba(248,81,73,0.12)]",
  },
  moderate: {
    border: "border-[rgba(210,153,34,0.4)]",
    icon:   "text-[#d29922]",
    badge:  "ACTION",
    badgeClass: "text-[#d29922] bg-[rgba(210,153,34,0.12)]",
  },
  routine: {
    border: "border-[#30363d]",
    icon:   "text-[#58a6ff]",
    badge:  "ROUTINE",
    badgeClass: "text-[#58a6ff] bg-[rgba(88,166,255,0.12)]",
  },
};

export function RecommendationCard({
  text,
  priority   = "routine",
  index,
  className,
}: RecommendationCardProps) {
  const cfg = PRIORITY_CONFIG[priority];

  return (
    <div
      className={cn(
        "flex items-start gap-3 p-3 rounded-md border bg-[#161b22]",
        cfg.border,
        className,
      )}
    >
      <AlertTriangle size={14} className={cn("flex-shrink-0 mt-0.5", cfg.icon)} />
      <div className="flex-1 min-w-0">
        <p className="text-[13px] text-[#c9d1d9] leading-snug">{text}</p>
      </div>
      {index !== undefined && (
        <span
          className={cn(
            "flex-shrink-0 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-sm",
            cfg.badgeClass,
          )}
        >
          {cfg.badge}
        </span>
      )}
    </div>
  );
}

// ── List wrapper ──────────────────────────────────────────────────────────────
interface RecommendationListProps {
  items:       string[];
  title?:      string;
  className?:  string;
}

export function RecommendationList({ items, title, className }: RecommendationListProps) {
  if (!items.length) return null;
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {title && (
        <p className="text-[11px] font-semibold uppercase tracking-wider text-[#8b949e]">
          {title}
        </p>
      )}
      {items.map((item, i) => (
        <RecommendationCard
          key={i}
          text={item}
          index={i}
          priority={i === 0 ? "urgent" : i < 3 ? "moderate" : "routine"}
        />
      ))}
    </div>
  );
}
