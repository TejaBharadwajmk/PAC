"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils/cn";
import { useSessionStore } from "@/lib/stores/useSessionStore";
import type { UserRole } from "@/types/api.types";
import {
  LayoutDashboard, FileText, Users, Dna, Map, Network,
  Bot, TrendingUp, BookOpen, Settings, ChevronLeft, ChevronRight,
  Shield,
} from "lucide-react";

interface NavItem {
  href:       string;
  label:      string;
  icon:       React.ElementType;
  roles:      UserRole[];
  badge?:     string;
  badgeColor?: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    href:  "/",
    label: "Dashboard",
    icon:  LayoutDashboard,
    roles: ["officer", "analyst", "supervisor", "admin"],
  },
  {
    href:  "/crimes",
    label: "Crimes",
    icon:  FileText,
    roles: ["officer", "analyst", "supervisor", "admin"],
  },
  {
    href:  "/criminals",
    label: "Criminals",
    icon:  Users,
    roles: ["officer", "analyst", "supervisor", "admin"],
  },
  {
    href:  "/dna",
    label: "Crime DNA",
    icon:  Dna,
    roles: ["analyst", "admin"],
    badge: "AI",
    badgeColor: "#58a6ff",
  },
  {
    href:  "/geo",
    label: "Geo Intelligence",
    icon:  Map,
    roles: ["analyst", "supervisor", "admin"],
  },
  {
    href:  "/network",
    label: "Network Explorer",
    icon:  Network,
    roles: ["analyst", "admin"],
    badge: "NEO4J",
    badgeColor: "#3fb950",
  },
  {
    href:  "/assistant",
    label: "AI Assistant",
    icon:  Bot,
    roles: ["officer", "analyst", "supervisor", "admin"],
    badge: "BETA",
    badgeColor: "#bc8cff",
  },
  {
    href:  "/predictions",
    label: "Predictions",
    icon:  TrendingUp,
    roles: ["analyst", "supervisor", "admin"],
    badge: "AI",
    badgeColor: "#58a6ff",
  },
  {
    href:  "/reports",
    label: "Reports",
    icon:  BookOpen,
    roles: ["officer", "analyst", "supervisor", "admin"],
  },
  {
    href:  "/admin",
    label: "Administration",
    icon:  Settings,
    roles: ["admin"],
  },
];

import { PacLogoEmblem } from "@/components/common/PacLogoEmblem";

export function Sidebar() {
  const pathname   = usePathname();
  const { user }   = useSessionStore();
  const [collapsed, setCollapsed] = useState(false);

  let role = user?.role as UserRole | undefined;
  if (!role && typeof document !== "undefined") {
    const roleMatch = document.cookie.match(/pac_role=([^;]+)/);
    if (roleMatch) role = roleMatch[1] as UserRole;
  }
  if (!role) role = "admin";

  const visible = NAV_ITEMS.filter((item) => item.roles.includes(role));

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside
      className={cn(
        "app-shell-sidebar flex flex-col bg-[#0d1117] border-r border-[#30363d] transition-all duration-200",
        collapsed ? "w-16" : "w-60",
      )}
    >
      {/* Logo */}
      <div className="flex items-center justify-between px-3 py-3.5 border-b border-[#30363d]">
        {!collapsed && (
          <div className="flex items-center gap-2.5">
            <PacLogoEmblem size={32} />
            <div className="leading-tight">
              <p className="text-[13px] font-bold text-[#e6edf3] tracking-wide flex items-center gap-1.5">
                PAC
                <span className="text-[9px] px-1 py-0.2 rounded bg-[#1f6feb]/20 text-[#58a6ff] border border-[#1f6feb]/40 font-mono font-semibold uppercase">
                  State Police
                </span>
              </p>
              <p className="text-[10px] text-[#8b949e] font-medium">Intelligence Core</p>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="mx-auto">
            <PacLogoEmblem size={28} />
          </div>
        )}

        <button
          onClick={() => setCollapsed((c) => !c)}
          className={cn(
            "p-1 rounded text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] transition-colors",
            collapsed && "mx-auto mt-2",
          )}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 flex flex-col gap-0.5">
        {visible.map((item) => {
          const Icon   = item.icon;
          const active = isActive(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center rounded-md transition-all duration-100 group",
                collapsed ? "justify-center p-2" : "gap-2.5 px-3 py-2",
                active
                  ? "bg-[#1f6feb1a] text-[#58a6ff] border border-[#1f6feb44]"
                  : "text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] border border-transparent",
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon
                size={16}
                className={cn(
                  "flex-shrink-0",
                  active ? "text-[#58a6ff]" : "text-[#8b949e] group-hover:text-[#e6edf3]",
                )}
              />
              {!collapsed && (
                <>
                  <span className="flex-1 text-[13px] font-medium truncate">
                    {item.label}
                  </span>
                  {item.badge && (
                    <span
                      className="text-[9px] font-bold font-mono px-1 py-0.5 rounded-sm"
                      style={{
                        color:           item.badgeColor,
                        backgroundColor: `${item.badgeColor}20`,
                        border:          `1px solid ${item.badgeColor}40`,
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User Profile Footer */}
      {user && !collapsed && (
        <div className="px-3 py-3 border-t border-[#30363d]">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-[#21262d] border border-[#30363d] flex items-center justify-center text-[11px] font-bold text-[#58a6ff]">
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-semibold text-[#e6edf3] truncate">
                {user.full_name}
              </p>
              <p className="text-[10px] text-[#8b949e] uppercase tracking-wider font-mono">
                {user.role} · {user.badge_number}
              </p>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
