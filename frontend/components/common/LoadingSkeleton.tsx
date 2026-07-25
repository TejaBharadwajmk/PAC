"use client";

import { cn } from "@/lib/utils/cn";

type SkeletonVariant = "dashboard" | "table" | "card" | "detail" | "map";

interface LoadingSkeletonProps {
  variant?: SkeletonVariant;
  className?: string;
}

function SkeletonBlock({ className }: { className?: string }) {
  return <div className={cn("skeleton", className)} />;
}

const VARIANTS: Record<SkeletonVariant, React.ReactNode> = {
  card: (
    <div className="pac-card flex flex-col gap-3">
      <SkeletonBlock className="h-3 w-24" />
      <SkeletonBlock className="h-8 w-16" />
      <SkeletonBlock className="h-3 w-32" />
    </div>
  ),
  dashboard: (
    <div className="p-6 flex flex-col gap-6">
      {/* KPI row */}
      <div className="grid grid-cols-3 gap-4 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="pac-card flex flex-col gap-3">
            <SkeletonBlock className="h-3 w-20" />
            <SkeletonBlock className="h-8 w-12" />
          </div>
        ))}
      </div>
      {/* Two-column content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="pac-card flex flex-col gap-3">
          <SkeletonBlock className="h-4 w-32" />
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonBlock key={i} className="h-12" />
          ))}
        </div>
        <div className="pac-card flex flex-col gap-3">
          <SkeletonBlock className="h-4 w-32" />
          <SkeletonBlock className="h-48" />
        </div>
      </div>
    </div>
  ),
  table: (
    <div className="flex flex-col gap-0">
      <div className="flex gap-4 px-3 py-2 bg-[#0d1117] border-b border-[#30363d]">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonBlock key={i} className="h-3 flex-1" />
        ))}
      </div>
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className="flex gap-4 px-3 py-3 border-b border-[#21262d]">
          {Array.from({ length: 6 }).map((_, j) => (
            <SkeletonBlock key={j} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  ),
  detail: (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-start gap-4">
        <SkeletonBlock className="w-16 h-16 rounded-full" />
        <div className="flex flex-col gap-2 flex-1">
          <SkeletonBlock className="h-6 w-48" />
          <SkeletonBlock className="h-4 w-32" />
          <SkeletonBlock className="h-4 w-24" />
        </div>
      </div>
      <div className="flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonBlock key={i} className="h-8 w-24 rounded" />
        ))}
      </div>
      <div className="pac-card">
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonBlock key={i} className={`h-4 mb-3 ${i % 3 === 2 ? "w-1/2" : "w-full"}`} />
        ))}
      </div>
    </div>
  ),
  map: (
    <div className="flex h-full">
      <div className="flex-1 skeleton" />
      <div className="w-80 pac-card flex flex-col gap-4 m-4">
        <SkeletonBlock className="h-4 w-24" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex flex-col gap-2">
            <SkeletonBlock className="h-3 w-full" />
            <SkeletonBlock className="h-3 w-3/4" />
          </div>
        ))}
      </div>
    </div>
  ),
};

export function LoadingSkeleton({ variant = "card", className }: LoadingSkeletonProps) {
  return (
    <div className={cn("animate-pulse w-full", className)}>
      {VARIANTS[variant]}
    </div>
  );
}
