"use client";

import { cn } from "@/lib/utils/cn";

interface PacLogoEmblemProps {
  size?: number;
  className?: string;
}

export function PacLogoEmblem({ size = 32, className }: PacLogoEmblemProps) {
  return (
    <div
      style={{ width: size, height: size }}
      className={cn(
        "rounded-lg bg-[#0d1117] border border-[#d4af37]/60 shadow-[0_0_12px_rgba(212,175,55,0.35)] flex items-center justify-center p-0.5 flex-shrink-0 transition-all duration-200",
        className
      )}
    >
      <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-[0_1px_4px_rgba(0,0,0,0.8)]">
        {/* Gold Crest Outer Ring */}
        <circle cx="50" cy="50" r="46" fill="none" stroke="#d4af37" strokeWidth="2.5" strokeDasharray="3 2" />
        <circle cx="50" cy="50" r="41" fill="#161b22" stroke="#d4af37" strokeWidth="1.5" />
        {/* Emblem Shield Red Center */}
        <path d="M50 18 L74 30 V55 C74 70 50 82 50 82 C50 82 26 70 26 55 V30 Z" fill="#b31217" stroke="#ffd700" strokeWidth="2" />
        {/* Gandaberunda Double-Headed Eagle Silhouette */}
        <path d="M50 24 L55 32 L65 28 L60 38 L68 44 L58 48 L62 60 L50 54 L38 60 L42 48 L32 44 L40 38 L35 28 L45 32 Z" fill="#ffd700" />
        {/* Lions Crest Crown */}
        <path d="M42 20 L50 14 L58 20 L54 22 L50 18 L46 22 Z" fill="#ffd700" />
      </svg>
    </div>
  );
}
