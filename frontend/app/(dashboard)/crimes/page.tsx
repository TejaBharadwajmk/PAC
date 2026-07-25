"use client";

import { useState } from "react";
import { useQuery }  from "@tanstack/react-query";
import Link          from "next/link";
import { crimesApi }  from "@/lib/api/crimes.api";
import { RiskBadge }  from "@/components/intelligence/RiskBadge";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import {
  KARNATAKA_DISTRICTS, CRIME_TYPE_LABELS, CRIME_STATUS_LABELS, STALE_TIME,
} from "@/lib/utils/constants";
import { severityToRiskLevel } from "@/lib/utils/riskLevel";
import type { CrimeType, CrimeStatus, CrimeSeverity } from "@/types/api.types";
import { format } from "date-fns";
import { Plus, Filter, FileText, ChevronLeft, ChevronRight, Search } from "lucide-react";

export default function CrimesListPage() {
  const [district, setDistrict]       = useState<string>("");
  const [crimeType, setCrimeType]     = useState<CrimeType | "">("");
  const [status, setStatus]           = useState<CrimeStatus | "">("");
  const [severity, setSeverity]       = useState<CrimeSeverity | "">("");
  const [page, setPage]               = useState<number>(1);

  const { data, isLoading } = useQuery({
    queryKey: ["crimes", "list", { district, crimeType, status, severity, page }],
    queryFn:  () =>
      crimesApi.list({
        district:   district || undefined,
        crime_type: (crimeType as CrimeType) || undefined,
        status:     (status as CrimeStatus) || undefined,
        severity:   (severity as CrimeSeverity) || undefined,
        page,
        page_size:  15,
      }),
    staleTime: STALE_TIME.crimes,
  });

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-bold text-[#e6edf3]">Crime Registry (FIRs)</h1>
          <p className="text-[13px] text-[#8b949e] mt-0.5">
            Registered First Information Reports across Karnataka police stations
          </p>
        </div>
        <Link
          href="/crimes/new"
          className="flex items-center gap-2 px-4 py-2 bg-[#1f6feb] hover:bg-[#388bfd] text-white text-[13px] font-semibold rounded transition-colors shadow-glow-blue"
        >
          <Plus size={14} />
          Register FIR
        </Link>
      </div>

      {/* Filter Bar */}
      <div className="pac-card flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 text-[#8b949e] text-[12px] font-semibold uppercase font-mono mr-2">
          <Filter size={14} />
          Filters:
        </div>

        {/* District Filter */}
        <select
          value={district}
          onChange={(e) => { setDistrict(e.target.value); setPage(1); }}
          className="bg-[#0d1117] border border-[#30363d] rounded text-[12px] text-[#e6edf3] px-3 py-1.5 focus:outline-none focus:border-[#58a6ff]"
        >
          <option value="">All Districts</option>
          {KARNATAKA_DISTRICTS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>

        {/* Crime Type Filter */}
        <select
          value={crimeType}
          onChange={(e) => { setCrimeType(e.target.value as CrimeType); setPage(1); }}
          className="bg-[#0d1117] border border-[#30363d] rounded text-[12px] text-[#e6edf3] px-3 py-1.5 focus:outline-none focus:border-[#58a6ff]"
        >
          <option value="">All Crime Types</option>
          {Object.entries(CRIME_TYPE_LABELS).map(([k, label]) => (
            <option key={k} value={k}>{label}</option>
          ))}
        </select>

        {/* Status Filter */}
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value as CrimeStatus); setPage(1); }}
          className="bg-[#0d1117] border border-[#30363d] rounded text-[12px] text-[#e6edf3] px-3 py-1.5 focus:outline-none focus:border-[#58a6ff]"
        >
          <option value="">All Statuses</option>
          {Object.entries(CRIME_STATUS_LABELS).map(([k, label]) => (
            <option key={k} value={k}>{label}</option>
          ))}
        </select>

        {/* Severity Filter */}
        <select
          value={severity}
          onChange={(e) => { setSeverity(e.target.value as CrimeSeverity); setPage(1); }}
          className="bg-[#0d1117] border border-[#30363d] rounded text-[12px] text-[#e6edf3] px-3 py-1.5 focus:outline-none focus:border-[#58a6ff]"
        >
          <option value="">All Severities</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>

        {/* Reset button */}
        {(district || crimeType || status || severity) && (
          <button
            onClick={() => { setDistrict(""); setCrimeType(""); setStatus(""); setSeverity(""); setPage(1); }}
            className="text-[12px] text-[#f85149] hover:underline ml-auto"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Table & Pagination */}
      <div className="pac-card flex flex-col gap-4">
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : !data?.items.length ? (
          <div className="py-16 text-center">
            <FileText size={36} className="text-[#484f58] mx-auto mb-3" />
            <p className="text-[14px] text-[#c9d1d9] font-medium">No crimes found</p>
            <p className="text-[12px] text-[#8b949e] mt-1">Try resetting or adjusting your search filters.</p>
          </div>
        ) : (
          <>
            <table className="pac-table">
              <thead>
                <tr>
                  <th className="text-left">FIR Number</th>
                  <th className="text-left">Crime Type</th>
                  <th className="text-left">Severity</th>
                  <th className="text-left">Status</th>
                  <th className="text-left">District</th>
                  <th className="text-left">Police Station</th>
                  <th className="text-left">Occurred Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((crime) => (
                  <tr
                    key={crime.id}
                    onClick={() => window.location.href = `/crimes/${crime.id}`}
                  >
                    <td>
                      <span className="font-mono text-[#58a6ff] text-[12px] font-semibold">
                        {crime.fir_number}
                      </span>
                    </td>
                    <td className="text-[#c9d1d9] font-medium">
                      {CRIME_TYPE_LABELS[crime.crime_type] ?? crime.crime_type}
                    </td>
                    <td>
                      <RiskBadge level={severityToRiskLevel(crime.severity)} size="sm" />
                    </td>
                    <td>
                      <span className="text-[12px] text-[#8b949e] font-mono capitalize">
                        {CRIME_STATUS_LABELS[crime.status] ?? crime.status}
                      </span>
                    </td>
                    <td className="text-[#c9d1d9]">{crime.district}</td>
                    <td className="text-[#8b949e] text-[12px]">{crime.police_station}</td>
                    <td className="text-[#8b949e] font-mono text-[12px]">
                      {format(new Date(crime.occurred_at), "dd MMM yyyy")}
                    </td>
                    <td>
                      <Link
                        href={`/crimes/${crime.id}`}
                        className="text-[12px] text-[#58a6ff] hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Details →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between border-t border-[#30363d] pt-3 text-[12px] text-[#8b949e]">
              <div>
                Showing page <span className="font-mono text-[#e6edf3]">{data.page}</span> of total{" "}
                <span className="font-mono text-[#e6edf3]">{data.total}</span> records
              </div>
              <div className="flex items-center gap-2">
                <button
                  disabled={!data.has_prev}
                  onClick={() => setPage((p) => p - 1)}
                  className="px-3 py-1 rounded bg-[#21262d] border border-[#30363d] text-[#e6edf3] disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#30363d] flex items-center gap-1"
                >
                  <ChevronLeft size={13} /> Prev
                </button>
                <button
                  disabled={!data.has_next}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1 rounded bg-[#21262d] border border-[#30363d] text-[#e6edf3] disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#30363d] flex items-center gap-1"
                >
                  Next <ChevronRight size={13} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
