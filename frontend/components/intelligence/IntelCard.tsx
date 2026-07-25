"use client";

import { type ReactNode } from "react";
import { cn } from "@/lib/utils/cn";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface IntelCardProps {
  title:       string;
  value:       string | number | ReactNode;
  subtitle?:   string;
  trend?:      number;   // positive = up, negative = down, 0 = flat
  trendLabel?: string;
  icon?:       ReactNode;
  severity?:   "critical" | "high" | "moderate" | "low" | "info" | "neutral";
  href?:       string;
  className?:  string;
  onClick?:    () => void;
}

const SEVERITY_BORDER: Record<string, string> = {
  critical: "border-[rgba(248,81,73,0.5)]",
  high:     "border-[rgba(233,141,48,0.4)]",
  moderate: "border-[rgba(210,153,34,0.4)]",
  low:      "border-[rgba(63,185,80,0.3)]",
  info:     "border-[rgba(88,166,255,0.3)]",
  neutral:  "border-[#30363d]",
};

const SEVERITY_TEXT: Record<string, string> = {
  critical: "text-[#f85149]",
  high:     "text-[#e98d30]",
  moderate: "text-[#d29922]",
  low:      "text-[#3fb950]",
  info:     "text-[#58a6ff]",
  neutral:  "text-[#e6edf3]",
};

export function IntelCard({
  title,
  value,
  subtitle,
  trend,
  trendLabel,
  icon,
  severity = "neutral",
  href,
  className,
  onClick,
}: IntelCardProps) {
  const isInteractive = !!href || !!onClick;
  const borderClass   = SEVERITY_BORDER[severity];
  const valueColour   = SEVERITY_TEXT[severity];

  const TrendIcon =
    trend === undefined ? null :
    trend > 0  ? TrendingUp :
    trend < 0  ? TrendingDown :
    Minus;

  const trendColour =
    trend === undefined ? "" :
    trend > 0  ? "text-[#f85149]" :   // up = worse for crime
    trend < 0  ? "text-[#3fb950]" :   // down = better
    "text-[#8b949e]";

  const card = (
    <div
      className={cn(
        "pac-card flex flex-col gap-3",
        `border ${borderClass}`,
        isInteractive && "cursor-pointer transition-all duration-150 hover:bg-[#1c2128] hover:border-[#58a6ff]/40",
        className,
      )}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-[#8b949e]">
          {title}
        </p>
        {icon && (
          <span className="text-[#8b949e] opacity-80">{icon}</span>
        )}
      </div>

      {/* Value */}
      <div className="flex items-end justify-between gap-2">
        <div className={cn("text-2xl font-bold leading-none font-mono", valueColour)}>
          {value}
        </div>

        {TrendIcon && trend !== undefined && (
          <div className={cn("flex items-center gap-1 text-[12px] font-semibold", trendColour)}>
            <TrendIcon size={14} />
            <span>{Math.abs(trend)}%</span>
          </div>
        )}
      </div>

      {/* Subtitle / trend label */}
      {(subtitle || trendLabel) && (
        <p className="text-[12px] text-[#8b949e] leading-tight">
          {subtitle ?? trendLabel}
        </p>
      )}
    </div>
  );

  if (href) {
    return <a href={href} className="no-underline">{card}</a>;
  }
  return card;
}
