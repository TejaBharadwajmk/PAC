"use client";

import { cn } from "@/lib/utils/cn";
import { confidenceToLabel, confidenceToColour, scoreToPercent } from "@/lib/utils/riskLevel";

interface ConfidenceMeterProps {
  /** 0.0 to 1.0 */
  score:     number;
  label?:    string;
  showValue?: boolean;
  className?: string;
}

export function ConfidenceMeter({
  score,
  label,
  showValue = true,
  className,
}: ConfidenceMeterProps) {
  const pct    = Math.min(Math.max(score, 0), 1) * 100;
  const colour = confidenceToColour(score);
  const text   = label ?? confidenceToLabel(score);

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-[#8b949e] uppercase tracking-wider font-semibold">
          Confidence
        </span>
        {showValue && (
          <span className="text-[12px] font-mono font-semibold" style={{ color: colour }}>
            {scoreToPercent(score)} — {text}
          </span>
        )}
      </div>
      <div className="confidence-bar-track">
        <div
          className="confidence-bar-fill"
          style={{ width: `${pct}%`, background: colour }}
        />
      </div>
    </div>
  );
}
