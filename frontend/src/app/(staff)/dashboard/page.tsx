"use client";

import { useMemo } from "react";

import { AdminDashboardView } from "@/app/(staff)/dashboard/_components/admin-dashboard";
import { ManagerDashboardView } from "@/app/(staff)/dashboard/_components/manager-dashboard";
import { TechnicianDashboardView } from "@/app/(staff)/dashboard/_components/technician-dashboard";
import { useSession } from "@/hooks/use-session";

export default function DashboardPage() {
  const { role } = useSession();

  const content = useMemo(() => {
    if (role === "ADMIN") {
      return <AdminDashboardView />;
    }
    if (role === "MANAGER") {
      return <ManagerDashboardView />;
    }
    return <TechnicianDashboardView />;
  }, [role]);

  return content;
}
