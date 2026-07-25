"use client";

import { useState } from "react";
import { useQuery }  from "@tanstack/react-query";
import Link          from "next/link";
import { criminalsApi } from "@/lib/api/criminals.api";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { KARNATAKA_DISTRICTS, STALE_TIME } from "@/lib/utils/constants";
import { Users, Search, Filter, ChevronLeft, ChevronRight, User, AlertTriangle } from "lucide-react";

export default function CriminalsListPage() {
  const [district, setDistrict]   = useState<string>("");
  const [search, setSearch]       = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["criminals", "list", { district, search }],
    queryFn:  () =>
      criminalsApi.list({
        district:    district || undefined,
        name_search: search || undefined,
      }),
    staleTime: STALE_TIME.criminals,
  });

  const criminalsList = Array.isArray(data) ? data : [];

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl">
      {/* Header */}
      <div>
        <h1 className="text-[18px] font-bold text-[#e6edf3]">Criminal Intelligence Database</h1>
        <p className="text-[13px] text-[#8b949e] mt-0.5">
          Comprehensive offender profiles, aliases, recidivism history, and risk scores
        </p>
      </div>

      {/* Filter & Search Bar */}
      <div className="pac-card flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8b949e]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search offender by name, alias, or ID…"
            className="w-full bg-[#0d1117] border border-[#30363d] rounded text-[12px] pl-9 pr-3 py-1.5 text-[#e6edf3] placeholder-[#484f58] focus:outline-none focus:border-[#58a6ff]"
          />
        </div>

        <select
          value={district}
          onChange={(e) => setDistrict(e.target.value)}
          className="bg-[#0d1117] border border-[#30363d] rounded text-[12px] text-[#e6edf3] px-3 py-1.5 focus:outline-none focus:border-[#58a6ff]"
        >
          <option value="">All Districts</option>
          {KARNATAKA_DISTRICTS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>

        {(district || search) && (
          <button
            onClick={() => { setDistrict(""); setSearch(""); }}
            className="text-[12px] text-[#f85149] hover:underline ml-auto"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Criminal Table */}
      <div className="pac-card flex flex-col gap-4">
        {isLoading ? (
          <LoadingSkeleton variant="table" />
        ) : !criminalsList.length ? (
          <div className="py-16 text-center">
            <Users size={36} className="text-[#484f58] mx-auto mb-3" />
            <p className="text-[14px] text-[#c9d1d9] font-medium">No offender profiles found</p>
            <p className="text-[12px] text-[#8b949e] mt-1">Try adjusting your search criteria.</p>
          </div>
        ) : (
          <table className="pac-table">
            <thead>
              <tr>
                <th className="text-left">Offender Name</th>
                <th className="text-left">Known Aliases</th>
                <th className="text-left">Primary District</th>
                <th className="text-left">Gang / Affiliation</th>
                <th className="text-left">Previous Cases</th>
                <th className="text-left">Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {criminalsList.map((criminal) => (
                <tr
                  key={criminal.id}
                  onClick={() => window.location.href = `/criminals/${criminal.id}`}
                >
                  <td>
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-[#21262d] border border-[#30363d] flex items-center justify-center text-[12px] font-bold text-[#58a6ff]">
                        <User size={14} />
                      </div>
                      <span className="font-semibold text-[#e6edf3] text-[13px]">
                        {criminal.name}
                      </span>
                    </div>
                  </td>
                  <td className="text-[#8b949e] text-[12px]">
                    {criminal.aliases?.length ? criminal.aliases.join(", ") : "None"}
                  </td>
                  <td className="text-[#c9d1d9] text-[12px]">{criminal.district || "Unassigned"}</td>
                  <td className="text-[#bc8cff] text-[12px] font-mono">
                    {criminal.gang_name || "Independent"}
                  </td>
                  <td className="font-mono text-[#58a6ff] text-[12px] font-semibold">
                    {criminal.previous_cases_count ?? 0} cases
                  </td>
                  <td>
                    {criminal.is_wanted ? (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#f85149]/15 text-[#f85149] border border-[#f85149]/30 flex items-center gap-1 w-fit">
                        <AlertTriangle size={11} /> WANTED
                      </span>
                    ) : (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#3fb950]/15 text-[#3fb950] border border-[#3fb950]/30">
                        {criminal.is_repeat_offender ? "REPEAT OFFENDER" : "REGISTERED"}
                      </span>
                    )}
                  </td>
                  <td>
                    <Link
                      href={`/criminals/${criminal.id}`}
                      className="text-[12px] text-[#58a6ff] hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Dossier →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
