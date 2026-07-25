"use client";

import { useState } from "react";
import { useQuery }  from "@tanstack/react-query";
import { authApi }    from "@/lib/api/auth.api";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { KARNATAKA_DISTRICTS, USER_ROLE_LABELS } from "@/lib/utils/constants";
import type { UserRole } from "@/types/api.types";
import { Users, Plus, Shield, CheckCircle2, UserCheck, AlertCircle } from "lucide-react";
import { toast } from "sonner";

export default function UserManagementPage() {
  const [isCreating, setIsCreating] = useState(false);
  const [badgeNumber, setBadgeNumber] = useState("");
  const [fullName, setFullName]       = useState("");
  const [email, setEmail]             = useState("");
  const [password, setPassword]       = useState("");
  const [district, setDistrict]       = useState("");
  const [station, setStation]         = useState("");
  const [role, setRole]               = useState<UserRole>("officer");

  const { data: me } = useQuery({
    queryKey: ["auth", "me"],
    queryFn:  authApi.me,
  });

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await authApi.register({
        badge_number:   badgeNumber,
        full_name:      fullName,
        email,
        password,
        district:       district || undefined,
        police_station: station || undefined,
        role,
      });

      toast.success(`Officer ${fullName} registered successfully!`);
      setIsCreating(false);
      setBadgeNumber("");
      setFullName("");
      setEmail("");
      setPassword("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to register officer";
      toast.error(msg);
    }
  };

  const sampleUsers = [
    { id: "1", badge_number: "KAR-1001", full_name: "Ramesh Kumar", email: "ramesh@karnataka.gov.in", district: "Bengaluru Urban", police_station: "Indiranagar PS", role: "officer", is_active: true },
    { id: "2", badge_number: "KAR-1002", full_name: "Priya Sharma", email: "priya@karnataka.gov.in", district: "Mysuru", police_station: "Central PS", role: "analyst", is_active: true },
    { id: "3", badge_number: "KAR-1000", full_name: "Inspector General Patil", email: "admin@karnataka.gov.in", district: "State HQ", police_station: "Command HQ", role: "admin", is_active: true },
  ];

  return (
    <div className="p-6 flex flex-col gap-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-bold text-[#e6edf3]">User & Role Management</h1>
          <p className="text-[13px] text-[#8b949e] mt-0.5">
            Administer law enforcement officer accounts, district assignments, and RBAC permissions
          </p>
        </div>

        <button
          onClick={() => setIsCreating((v) => !v)}
          className="flex items-center gap-2 px-4 py-2 bg-[#1f6feb] hover:bg-[#388bfd] text-white text-[13px] font-semibold rounded transition-colors shadow-glow-blue"
        >
          <Plus size={14} />
          {isCreating ? "Cancel" : "Register Officer"}
        </button>
      </div>

      {/* Register Form Modal/Panel */}
      {isCreating && (
        <form onSubmit={handleRegister} className="pac-card flex flex-col gap-4 border-[#1f6feb]/50 animate-fade-in">
          <h2 className="text-[14px] font-semibold text-[#e6edf3]">Register New Officer Account</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[12px]">
            <div>
              <label className="text-[#8b949e] font-semibold">Badge Number *</label>
              <input
                type="text"
                required
                value={badgeNumber}
                onChange={(e) => setBadgeNumber(e.target.value)}
                placeholder="e.g. KAR-1004"
                className="w-full bg-[#0d1117] border border-[#30363d] rounded p-2 text-[#e6edf3] font-mono"
              />
            </div>
            <div>
              <label className="text-[#8b949e] font-semibold">Full Name *</label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Officer Full Name"
                className="w-full bg-[#0d1117] border border-[#30363d] rounded p-2 text-[#e6edf3]"
              />
            </div>
            <div>
              <label className="text-[#8b949e] font-semibold">Email Address *</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="officer@karnataka.gov.in"
                className="w-full bg-[#0d1117] border border-[#30363d] rounded p-2 text-[#e6edf3]"
              />
            </div>
            <div>
              <label className="text-[#8b949e] font-semibold">Password *</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                className="w-full bg-[#0d1117] border border-[#30363d] rounded p-2 text-[#e6edf3]"
              />
            </div>
            <div>
              <label className="text-[#8b949e] font-semibold">District Assignment</label>
              <select
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="w-full bg-[#0d1117] border border-[#30363d] rounded p-2 text-[#e6edf3]"
              >
                <option value="">Select district…</option>
                {KARNATAKA_DISTRICTS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[#8b949e] font-semibold">Assign Role *</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                className="w-full bg-[#0d1117] border border-[#30363d] rounded p-2 text-[#e6edf3]"
              >
                <option value="officer">Officer (Field)</option>
                <option value="analyst">Analyst (Intel)</option>
                <option value="supervisor">Supervisor (Command)</option>
                <option value="admin">Administrator</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="w-full py-2 bg-[#3fb950] text-white text-[13px] font-semibold rounded hover:bg-[#2ea043]"
          >
            Create Officer Account
          </button>
        </form>
      )}

      {/* Users Table */}
      <div className="pac-card flex flex-col gap-3">
        <h2 className="text-[14px] font-semibold text-[#e6edf3]">Officer Accounts</h2>
        <table className="pac-table">
          <thead>
            <tr>
              <th className="text-left">Badge</th>
              <th className="text-left">Name</th>
              <th className="text-left">Email</th>
              <th className="text-left">District</th>
              <th className="text-left">Station</th>
              <th className="text-left">Role</th>
              <th className="text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {sampleUsers.map((u) => (
              <tr key={u.id}>
                <td><span className="font-mono text-[#58a6ff] text-[12px] font-bold">{u.badge_number}</span></td>
                <td className="text-[#e6edf3] font-semibold text-[13px]">{u.full_name}</td>
                <td className="text-[#8b949e] text-[12px]">{u.email}</td>
                <td className="text-[#c9d1d9] text-[12px]">{u.district}</td>
                <td className="text-[#8b949e] text-[12px]">{u.police_station}</td>
                <td>
                  <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-[#21262d] border border-[#30363d] text-[#bc8cff]">
                    {USER_ROLE_LABELS[u.role] ?? u.role}
                  </span>
                </td>
                <td>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#3fb950]/15 text-[#3fb950] border border-[#3fb950]/30">
                    ACTIVE
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
