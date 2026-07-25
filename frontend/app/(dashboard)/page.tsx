"use client";

import { useSessionStore } from "@/lib/stores/useSessionStore";

// Each role dashboard is a separate async component for code splitting
import dynamic from "next/dynamic";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";

const OfficerDashboard    = dynamic(() => import("@/modules/dashboard/OfficerDashboard"),    { loading: () => <LoadingSkeleton variant="dashboard" /> });
const AnalystDashboard    = dynamic(() => import("@/modules/dashboard/AnalystDashboard"),    { loading: () => <LoadingSkeleton variant="dashboard" /> });
const SupervisorDashboard = dynamic(() => import("@/modules/dashboard/SupervisorDashboard"), { loading: () => <LoadingSkeleton variant="dashboard" /> });
const AdminDashboard      = dynamic(() => import("@/modules/dashboard/AdminDashboard"),      { loading: () => <LoadingSkeleton variant="dashboard" /> });

export default function DashboardPage() {
  const { user } = useSessionStore();

  if (!user) {
    return null;
  }

  switch (user.role) {
    case "analyst":    return <AnalystDashboard />;
    case "supervisor": return <SupervisorDashboard />;
    case "admin":      return <AdminDashboard />;
    default:           return <OfficerDashboard />;
  }
}
