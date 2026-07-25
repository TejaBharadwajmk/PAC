"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { assistantApi } from "@/lib/api/assistant.api";
import { KARNATAKA_DISTRICTS, REPORT_TYPE_LABELS } from "@/lib/utils/constants";
import { EvidenceList }       from "@/components/intelligence/EvidenceList";
import { RecommendationList } from "@/components/intelligence/RecommendationCard";
import type { ReportType, ReportResponse } from "@/types/api.types";
import { BookOpen, Sparkles, Printer, ArrowLeft, CheckCircle2, FileText } from "lucide-react";
import { toast } from "sonner";

export default function NewReportPage() {
  const router                       = useRouter();
  const [reportType, setReportType]   = useState<ReportType>("fir_investigation");
  const [crimeId, setCrimeId]         = useState("");
  const [criminalId, setCriminalId]   = useState("");
  const [district, setDistrict]       = useState("");
  const [gangName, setGangName]       = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [report, setReport]           = useState<ReportResponse | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);
    try {
      const res = await assistantApi.generateReport({
        report_type: reportType,
        crime_id:    crimeId || undefined,
        criminal_id: criminalId || undefined,
        district:    district || undefined,
        gang_name:   gangName || undefined,
      });

      setReport(res);
      toast.success("Intelligence report generated!");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to generate report";
      toast.error(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto flex flex-col gap-6">
      <div className="flex items-center justify-between no-print">
        <button
          onClick={() => router.push("/reports")}
          className="flex items-center gap-1 text-[13px] text-[#8b949e] hover:text-[#e6edf3]"
        >
          <ArrowLeft size={14} /> Back to Reports Archive
        </button>

        {report && (
          <button
            onClick={() => window.print()}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#3fb950] text-white text-[13px] font-semibold rounded hover:bg-[#2ea043] transition-colors"
          >
            <Printer size={14} /> Print / Export PDF
          </button>
        )}
      </div>

      {!report ? (
        <form onSubmit={handleGenerate} className="pac-card flex flex-col gap-5 border-[#1f6feb]/40">
          <div>
            <h1 className="text-[16px] font-bold text-[#e6edf3] flex items-center gap-2">
              <Sparkles size={18} className="text-[#bc8cff]" />
              Structured Intelligence Report Generator
            </h1>
            <p className="text-[13px] text-[#8b949e] mt-0.5">
              Generates official law enforcement intelligence summaries backed by PAC evidence facts
            </p>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-[#8b949e]">Select Report Template *</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value as ReportType)}
              className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
            >
              {Object.entries(REPORT_TYPE_LABELS).map(([k, label]) => (
                <option key={k} value={k}>{label}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] font-semibold text-[#8b949e]">Crime ID (Optional)</label>
              <input
                type="text"
                value={crimeId}
                onChange={(e) => setCrimeId(e.target.value)}
                placeholder="Crime UUID..."
                className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] font-mono focus:outline-none focus:border-[#58a6ff]"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] font-semibold text-[#8b949e]">Criminal ID (Optional)</label>
              <input
                type="text"
                value={criminalId}
                onChange={(e) => setCriminalId(e.target.value)}
                placeholder="Criminal UUID..."
                className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] font-mono focus:outline-none focus:border-[#58a6ff]"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] font-semibold text-[#8b949e]">District Filter (Optional)</label>
              <select
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
              >
                <option value="">Select district...</option>
                {KARNATAKA_DISTRICTS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] font-semibold text-[#8b949e]">Gang Name (Optional)</label>
              <input
                type="text"
                value={gangName}
                onChange={(e) => setGangName(e.target.value)}
                placeholder="e.g. D-Company..."
                className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isGenerating}
            className="w-full py-2.5 bg-[#1f6feb] hover:bg-[#388bfd] disabled:opacity-40 text-white font-semibold text-[13px] rounded transition-colors flex items-center justify-center gap-2"
          >
            {isGenerating ? "Generating Intelligence Report…" : "Compile & Generate Report"}
          </button>
        </form>
      ) : (
        /* Formatted Official Intelligence Report Printable Document */
        <div className="bg-white text-black p-8 rounded-lg shadow-elevated flex flex-col gap-6 font-sans border border-gray-300">
          <div className="border-b-2 border-black pb-4 flex justify-between items-start">
            <div>
              <h1 className="text-xl font-bold uppercase tracking-wide text-gray-900">
                {report.title}
              </h1>
              <p className="text-xs text-gray-600 uppercase font-mono mt-1">
                KARNATAKA POLICE DEPARTMENT · OFFICIAL INTELLIGENCE BRIEF
              </p>
            </div>
            <span className="text-xs font-mono border border-red-600 text-red-600 px-2 py-1 uppercase font-bold">
              CONFIDENTIAL
            </span>
          </div>

          <div>
            <h2 className="text-sm font-bold uppercase text-gray-800 border-b border-gray-300 pb-1 mb-2">
              1. Executive Summary
            </h2>
            <p className="text-xs text-gray-700 leading-relaxed">{report.executive_summary}</p>
          </div>

          <div>
            <h2 className="text-sm font-bold uppercase text-gray-800 border-b border-gray-300 pb-1 mb-2">
              2. Key Findings
            </h2>
            <ul className="list-disc pl-5 text-xs text-gray-700 flex flex-col gap-1">
              {report.key_findings.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className="text-sm font-bold uppercase text-gray-800 border-b border-gray-300 pb-1 mb-2">
              3. Evidence Base
            </h2>
            <ul className="list-decimal pl-5 text-xs text-gray-700 flex flex-col gap-1">
              {report.evidence.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className="text-sm font-bold uppercase text-gray-800 border-b border-gray-300 pb-1 mb-2">
              4. Operational Recommendations
            </h2>
            <ul className="list-disc pl-5 text-xs text-gray-700 flex flex-col gap-1">
              {report.recommendations.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>

          <div className="border-t border-gray-400 pt-4 flex justify-between items-center text-[10px] font-mono text-gray-500">
            <span>GENERATED BY PAC AI ENGINE v1.0</span>
            <span>VERIFIED FOR OPERATIONAL USE</span>
          </div>
        </div>
      )}
    </div>
  );
}
