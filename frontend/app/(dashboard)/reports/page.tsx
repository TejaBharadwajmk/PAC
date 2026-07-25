"use client";

import Link from "next/link";
import { BookOpen, Plus, FileText, Printer, ArrowRight } from "lucide-react";
import { REPORT_TYPE_LABELS } from "@/lib/utils/constants";

export default function ReportsPage() {
  const sampleReports = [
    { id: "1", title: "FIR Investigation Intelligence Report — FIR-2026-BLR-0042", type: "fir_investigation", date: "2026-07-20" },
    { id: "2", title: "District Crime Hotspot Assessment — Bengaluru Urban", type: "hotspot_assessment", date: "2026-07-19" },
    { id: "3", title: "Criminal Intelligence Profile Brief — Offender #CR-104", type: "criminal_intelligence", date: "2026-07-18" },
  ];

  return (
    <div className="p-6 flex flex-col gap-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-bold text-[#e6edf3]">Intelligence Reports</h1>
          <p className="text-[13px] text-[#8b949e] mt-0.5">
            Structured police intelligence briefs, FIR investigations, and district threat reports
          </p>
        </div>

        <Link
          href="/reports/new"
          className="flex items-center gap-2 px-4 py-2 bg-[#1f6feb] hover:bg-[#388bfd] text-white text-[13px] font-semibold rounded transition-colors shadow-glow-blue"
        >
          <Plus size={14} />
          Generate New Report
        </Link>
      </div>

      <div className="pac-card flex flex-col gap-3">
        <h2 className="text-[14px] font-semibold text-[#e6edf3]">Generated Reports Archive</h2>
        <div className="flex flex-col gap-2">
          {sampleReports.map((r) => (
            <div
              key={r.id}
              className="flex items-center justify-between p-3.5 bg-[#0d1117] rounded border border-[#30363d] hover:border-[#58a6ff]/40 transition-colors"
            >
              <div className="flex items-center gap-3">
                <FileText size={18} className="text-[#58a6ff]" />
                <div>
                  <p className="text-[13px] font-semibold text-[#e6edf3]">{r.title}</p>
                  <p className="text-[11px] text-[#8b949e]">
                    {REPORT_TYPE_LABELS[r.type]} · Generated {r.date}
                  </p>
                </div>
              </div>
              <button
                onClick={() => window.print()}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#21262d] border border-[#30363d] text-[#e6edf3] text-[12px] rounded hover:bg-[#30363d]"
              >
                <Printer size={13} /> Print / Export PDF
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
