"use client";

import { cn } from "@/lib/utils/cn";
import { CheckCircle2, AlertTriangle, Info } from "lucide-react";

interface EvidenceListProps {
  items:      string[];
  title?:     string;
  variant?:   "evidence" | "recommendation" | "finding";
  className?: string;
  maxItems?:  number;
}

const VARIANT_CONFIG = {
  evidence: {
    icon:       CheckCircle2,
    iconColour: "#58a6ff",
    prefix:     "E",
  },
  recommendation: {
    icon:       AlertTriangle,
    iconColour: "#d29922",
    prefix:     "R",
  },
  finding: {
    icon:       Info,
    iconColour: "#3fb950",
    prefix:     "F",
  },
};

export function EvidenceList({
  items,
  title,
  variant    = "evidence",
  className,
  maxItems,
}: EvidenceListProps) {
  if (!items.length) return null;

  const cfg         = VARIANT_CONFIG[variant];
  const Icon        = cfg.icon;
  const displayItems = maxItems ? items.slice(0, maxItems) : items;
  const hidden       = maxItems && items.length > maxItems ? items.length - maxItems : 0;

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {title && (
        <p className="text-[11px] font-semibold uppercase tracking-wider text-[#8b949e]">
          {title}
        </p>
      )}
      <ol className="flex flex-col gap-1.5">
        {displayItems.map((item, i) => (
          <li key={i} className="flex items-start gap-2 group">
            <span
              className="flex-shrink-0 mt-0.5"
              style={{ color: cfg.iconColour }}
            >
              <Icon size={13} />
            </span>
            <span className="text-[13px] text-[#c9d1d9] leading-snug">{item}</span>
          </li>
        ))}
      </ol>
      {hidden > 0 && (
        <p className="text-[11px] text-[#8b949e]">
          +{hidden} more items
        </p>
      )}
    </div>
  );
}
