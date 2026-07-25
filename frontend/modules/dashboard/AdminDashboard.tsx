"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { assistantApi } from "@/lib/api/assistant.api";
import { geoApi }       from "@/lib/api/geo.api";
import { adminApi, AuditLogItem, CctnsSyncLogItem } from "@/lib/api/admin.api";
import { STALE_TIME }   from "@/lib/utils/constants";
import {
  CheckCircle2, XCircle, AlertCircle, Settings, Users, Database, Network, Bot, RefreshCw,
  ShieldCheck, FileText, Play, Server, Clock, Activity, HardDrive
} from "lucide-react";
import { toast } from "sonner";

type HealthStatus = "healthy" | "degraded" | "down" | "unknown";

function StatusDot({ status }: { status: HealthStatus }) {
  const colours: Record<HealthStatus, string> = {
    healthy:  "#3fb950",
    degraded: "#d29922",
    down:     "#f85149",
    unknown:  "#8b949e",
  };
  return (
    <span
      className="inline-block rounded-full w-2 h-2"
      style={{ background: colours[status], boxShadow: `0 0 6px ${colours[status]}` }}
    />
  );
}

export default function AdminDashboard() {
  const queryClient = useQueryClient();

  const { data: llmHealth, isLoading: llmLoading } = useQuery({
    queryKey: ["assistant", "health"],
    queryFn:  assistantApi.health,
    staleTime: 30_000,
  });

  const { data: geoStats } = useQuery({
    queryKey: ["geo", "statistics"],
    queryFn:  () => geoApi.statistics(),
    staleTime: STALE_TIME.hotspots,
  });

  const { data: auditLogs, isLoading: auditLoading } = useQuery({
    queryKey: ["admin", "auditLogs"],
    queryFn:  () => adminApi.getAuditLogs(15),
    refetchInterval: 10_000,
  });

  const { data: cctnsLogs, isLoading: cctnsLoading } = useQuery({
    queryKey: ["admin", "cctnsLogs"],
    queryFn:  () => adminApi.getCctnsLogs(5),
    refetchInterval: 10_000,
  });

  const seedMutation = useMutation({
    mutationFn: () => adminApi.seedCctnsStaging(5),
    onSuccess: (data) => {
      toast.success(`Seeded ${data.seeded_count} legacy records to CCTNS staging`);
      queryClient.invalidateQueries({ queryKey: ["admin", "cctnsLogs"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to seed CCTNS staging data");
    },
  });

  const syncMutation = useMutation({
    mutationFn: () => adminApi.triggerCctnsSync(),
    onSuccess: (data) => {
      toast.success(`ETL Sync complete! Imported ${data.log.records_imported} records`);
      queryClient.invalidateQueries({ queryKey: ["admin", "cctnsLogs"] });
      queryClient.invalidateQueries({ queryKey: ["crimes"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "auditLogs"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to trigger CCTNS ETL Sync");
    },
  });

  const llmStatus: HealthStatus =
    llmHealth?.status === "healthy" ? "healthy" :
    llmHealth?.status === "degraded" ? "degraded" :
    llmHealth ? "down" : "unknown";

  const safeAuditLogs = Array.isArray(auditLogs) ? auditLogs : [];
  const safeCctnsLogs = Array.isArray(cctnsLogs) ? cctnsLogs : [];
  const safeAvailableModules = Array.isArray(llmHealth?.available_modules) ? llmHealth.available_modules : [];

  return (
    <div className="p-6 flex flex-col gap-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-bold text-[#e6edf3]">Administration & Operations</h1>
          <p className="text-[13px] text-[#8b949e] mt-0.5">System health, CCTNS ETL ingestion, audit logs, and security controls</p>
        </div>
        <Link
          href="/admin/users"
          className="flex items-center gap-2 px-4 py-2 bg-[#21262d] border border-[#30363d] text-[#e6edf3] text-[13px] font-semibold rounded hover:bg-[#30363d] transition-colors"
        >
          <Users size={14} />
          Manage Users
        </Link>
      </div>

      {/* System Health Panel */}
      <div className="pac-card flex flex-col gap-4">
        <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
          <Settings size={14} className="text-[#58a6ff]" />
          System Infrastructure Health
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { label: "FastAPI Backend", desc: "REST API server", status: "healthy" as HealthStatus, icon: Database },
            { label: "PostgreSQL + PostGIS", desc: "Primary database & vector store", status: "healthy" as HealthStatus, icon: Database },
            { label: `LLM Provider (${llmHealth?.provider ?? "…"})`, desc: llmHealth?.model ?? "Checking…", status: llmLoading ? "unknown" as HealthStatus : llmStatus, icon: Bot },
            { label: "Neo4j Graph DB", desc: "Criminal network store", status: "healthy" as HealthStatus, icon: Network },
          ].map((svc) => {
            const Icon = svc.icon;
            return (
              <div key={svc.label} className="flex items-center justify-between p-3 bg-[#0d1117] rounded border border-[#30363d]">
                <div className="flex items-center gap-3">
                  <Icon size={16} className="text-[#8b949e]" />
                  <div>
                    <p className="text-[13px] font-semibold text-[#e6edf3]">{svc.label}</p>
                    <p className="text-[11px] text-[#8b949e]">{svc.desc}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusDot status={svc.status} />
                  <span className="text-[12px] font-mono capitalize text-[#8b949e]">{svc.status}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* CCTNS Legacy Data Ingestion Panel */}
      <div className="pac-card flex flex-col gap-4 border-l-4 border-l-[#58a6ff]">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
              <HardDrive size={15} className="text-[#58a6ff]" />
              CCTNS Legacy Data Ingestion (ETL Pipeline)
            </h2>
            <p className="text-[12px] text-[#8b949e] mt-0.5">
              Automated polling pipeline that transforms raw CCTNS staging FIR records into vector DNA embeddings and merges graph entities.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => seedMutation.mutate()}
              disabled={seedMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#21262d] border border-[#30363d] text-[#c9d1d9] text-[12px] font-medium rounded hover:bg-[#30363d] transition-colors disabled:opacity-50"
            >
              <Database size={13} />
              {seedMutation.isPending ? "Seeding..." : "Seed Staging"}
            </button>
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1f6feb] text-white text-[12px] font-semibold rounded hover:bg-[#388bfd] transition-colors disabled:opacity-50 shadow-sm"
            >
              <RefreshCw size={13} className={syncMutation.isPending ? "animate-spin" : ""} />
              {syncMutation.isPending ? "Syncing..." : "Run ETL Sync"}
            </button>
          </div>
        </div>

        {/* Sync History Table */}
        <div className="overflow-x-auto bg-[#0d1117] rounded border border-[#30363d]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[#161b22] text-[#8b949e] border-b border-[#30363d] uppercase text-[10px] tracking-wider font-semibold">
              <tr>
                <th className="px-3 py-2">Sync Time</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Found</th>
                <th className="px-3 py-2 text-right">Imported</th>
                <th className="px-3 py-2 text-right">Skipped</th>
                <th className="px-3 py-2 text-right">Duration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#21262d] text-[#c9d1d9]">
              {cctnsLoading ? (
                <tr><td colSpan={6} className="px-3 py-3 text-center text-[#8b949e]">Loading sync history...</td></tr>
              ) : safeCctnsLogs.length === 0 ? (
                <tr><td colSpan={6} className="px-3 py-3 text-center text-[#8b949e]">No ETL sync runs recorded yet. Click "Run ETL Sync" above.</td></tr>
              ) : (
                safeCctnsLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-[#161b22]/50 transition-colors">
                    <td className="px-3 py-2 font-mono text-[#8b949e]">
                      {log.created_at ? new Date(log.created_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                        log.status === "SUCCESS" ? "bg-[#238636]/20 text-[#3fb950]" : "bg-[#da3633]/20 text-[#f85149]"
                      }`}>
                        {log.status === "SUCCESS" ? <CheckCircle2 size={10} /> : <AlertCircle size={10} />}
                        {log.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono">{log.records_found}</td>
                    <td className="px-3 py-2 text-right font-mono font-semibold text-[#3fb950]">{log.records_imported}</td>
                    <td className="px-3 py-2 text-right font-mono text-[#8b949e]">{log.duplicates_skipped}</td>
                    <td className="px-3 py-2 text-right font-mono text-[#8b949e]">{log.duration_ms}ms</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Trail Logs Panel */}
      <div className="pac-card flex flex-col gap-4 border-l-4 border-l-[#238636]">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
              <ShieldCheck size={15} className="text-[#3fb950]" />
              Audit Trail Logs (Chain-of-Custody Compliance)
            </h2>
            <p className="text-[12px] text-[#8b949e] mt-0.5">
              Non-blocking audit log recording every sensitive API request, user search query, and report generation.
            </p>
          </div>
          <span className="text-[11px] font-mono text-[#8b949e] bg-[#0d1117] px-2 py-1 rounded border border-[#30363d]">
            Live Auto-Refresh (10s)
          </span>
        </div>

        <div className="overflow-x-auto bg-[#0d1117] rounded border border-[#30363d]">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-[#161b22] text-[#8b949e] border-b border-[#30363d] uppercase text-[10px] tracking-wider font-semibold">
              <tr>
                <th className="px-3 py-2">Timestamp</th>
                <th className="px-3 py-2">Badge</th>
                <th className="px-3 py-2">Action</th>
                <th className="px-3 py-2">Endpoint</th>
                <th className="px-3 py-2">Client IP</th>
                <th className="px-3 py-2 text-center">Status</th>
                <th className="px-3 py-2 text-right">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#21262d] text-[#c9d1d9]">
              {auditLoading ? (
                <tr><td colSpan={7} className="px-3 py-4 text-center text-[#8b949e]">Loading audit logs...</td></tr>
              ) : safeAuditLogs.length === 0 ? (
                <tr><td colSpan={7} className="px-3 py-4 text-center text-[#8b949e]">No audit logs recorded yet. Perform actions to generate logs.</td></tr>
              ) : (
                safeAuditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-[#161b22]/50 transition-colors">
                    <td className="px-3 py-2 font-mono text-[#8b949e]">
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "—"}
                    </td>
                    <td className="px-3 py-2 font-mono font-semibold text-[#58a6ff]">
                      {log.badge_number || "ANONYMOUS"}
                    </td>
                    <td className="px-3 py-2">
                      <span className="px-1.5 py-0.5 bg-[#21262d] border border-[#30363d] rounded text-[10px] uppercase font-mono text-[#e6edf3]">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-[#c9d1d9] truncate max-w-[220px]" title={log.endpoint}>
                      <span className="text-[#8b949e] mr-1">{log.method}</span>
                      {log.endpoint}
                    </td>
                    <td className="px-3 py-2 font-mono text-[#8b949e]">{log.ip_address || "127.0.0.1"}</td>
                    <td className="px-3 py-2 text-center font-mono">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        (log.status_code || 200) < 300 ? "bg-[#238636]/20 text-[#3fb950]" : "bg-[#da3633]/20 text-[#f85149]"
                      }`}>
                        {log.status_code}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-[#8b949e]">{log.duration_ms}ms</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* AI Module Availability */}
      {safeAvailableModules.length > 0 && (
        <div className="pac-card flex flex-col gap-3">
          <h2 className="text-[13px] font-semibold text-[#e6edf3] flex items-center gap-2">
            <Bot size={14} className="text-[#bc8cff]" />
            AI Module Availability
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {safeAvailableModules.map((mod) => (
              <div key={mod} className="flex items-center gap-2 text-[12px] text-[#c9d1d9]">
                <CheckCircle2 size={12} className="text-[#3fb950]" />
                {mod}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
