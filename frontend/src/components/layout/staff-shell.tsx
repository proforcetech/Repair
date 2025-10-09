"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useMemo, useState } from "react";
import { clsx } from "clsx";

import { useDashboardNotifications } from "@/hooks/use-dashboard-data";
import { useSession } from "@/hooks/use-session";
import { useLayoutStore } from "@/stores/layout-store";
import type { DashboardNotification } from "@/services/dashboard-mappers";

const navigationByRole: Record<string, Array<{ label: string; href: string }>> = {
  TECHNICIAN: [
    { label: "My Dashboard", href: "/dashboard" },
    { label: "Manager View", href: "/dashboard/manager" },
    { label: "Invoices", href: "/invoices" },
    { label: "Inventory", href: "/inventory" },
  ],
  MANAGER: [
    { label: "Manager Dashboard", href: "/dashboard/manager" },
    { label: "Technician View", href: "/dashboard" },
    { label: "Admin Summary", href: "/dashboard/admin" },
    { label: "Invoices", href: "/invoices" },
    { label: "Inventory", href: "/inventory" },
  ],
  ADMIN: [
    { label: "Admin Dashboard", href: "/dashboard/admin" },
    { label: "Manager Dashboard", href: "/dashboard/manager" },
    { label: "Technician Dashboard", href: "/dashboard" },
    { label: "Invoices", href: "/invoices" },
    { label: "Inventory", href: "/inventory" },
  ],
};

const statusColor: Record<string, string> = {
  info: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  muted: "bg-muted text-muted-foreground",
};

type StaffShellProps = {
  children: ReactNode;
};

export function StaffShell({ children }: StaffShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { isSidebarOpen, toggleSidebar, closeSidebar } = useLayoutStore();
  const { user, isAuthenticated, role, isLoading } = useSession();
  const [isSigningOut, setIsSigningOut] = useState(false);

  const breadcrumbs = useMemo(() => {
    if (!pathname) {
      return [];
    }
    const segments = pathname.split("/").filter(Boolean);
    return segments.map((segment, index) => {
      const href = `/${segments.slice(0, index + 1).join("/")}`;
      const label = segment
        .replace(/\(.*\)/g, "")
        .replace(/[-_]/g, " ")
        .replace(/\b\w/g, (match) => match.toUpperCase())
        .trim();
      return { href, label: label || "Dashboard" };
    });
  }, [pathname]);

  const navigation =
    navigationByRole[role ?? ""] ?? [
      { label: "Dashboard", href: "/dashboard" },
      { label: "Invoices", href: "/invoices" },
    ];
  const { data: notifications } = useDashboardNotifications(role ?? null);

  if (!isAuthenticated && !isLoading) {
    router.replace("/login");
  }

  const handleSignOut = async () => {
    setIsSigningOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      router.replace("/login");
      router.refresh();
    } finally {
      setIsSigningOut(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/90 backdrop-blur">
        <div className="container flex h-16 items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={toggleSidebar}
              className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border text-foreground transition-colors hover:bg-accent lg:hidden"
              aria-label="Toggle navigation"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            </button>
            <Link href="/dashboard" className="flex items-center gap-2 text-sm font-semibold">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground shadow">AR</span>
              <span className="hidden sm:inline">Staff Operations</span>
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <Breadcrumbs items={breadcrumbs} />
            <NotificationCenter notifications={notifications ?? []} />
            {isAuthenticated && (
              <div className="hidden flex-col text-xs leading-tight sm:flex">
                <span className="font-semibold text-foreground">{user?.email}</span>
                <span className="uppercase tracking-wide text-muted-foreground">{role}</span>
              </div>
            )}
            {isAuthenticated && (
              <button
                type="button"
                onClick={handleSignOut}
                className="inline-flex items-center rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
                disabled={isSigningOut}
              >
                {isSigningOut ? "Signing out…" : "Sign out"}
              </button>
            )}
          </div>
        </div>
      </header>
      <div className="flex flex-1">
        <aside
          className={clsx(
            "fixed inset-y-0 left-0 z-30 w-64 border-r border-border/60 bg-background/95 px-4 py-6 transition-transform duration-200 ease-in-out lg:static lg:translate-x-0",
            isSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
          )}
        >
          <nav className="space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={closeSidebar}
                  className={clsx(
                    "flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary shadow"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  )}
                >
                  {item.label}
                  {isActive && (
                    <span className="inline-flex h-2 w-2 rounded-full bg-primary" />
                  )}
                </Link>
              );
            })}
          </nav>
        </aside>
        {isSidebarOpen && (
          <button
            type="button"
            aria-label="Close sidebar overlay"
            className="fixed inset-0 z-20 bg-black/40 backdrop-blur-sm lg:hidden"
            onClick={closeSidebar}
          />
        )}
        <main className="flex-1 bg-gradient-to-b from-background to-background/90">
          <div className="container py-8">
            <div className="rounded-xl border border-border/60 bg-card/80 p-6 shadow-sm backdrop-blur">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

type BreadcrumbsProps = {
  items: Array<{ href: string; label: string }>;
};

function Breadcrumbs({ items }: BreadcrumbsProps) {
  if (!items.length) {
    return null;
  }

  return (
    <nav aria-label="Breadcrumb" className="hidden items-center gap-1 text-xs text-muted-foreground sm:flex">
      {items.map((item, index) => (
        <span key={item.href} className="flex items-center gap-1">
          {index > 0 && <span className="opacity-50">/</span>}
          <Link href={item.href} className="hover:text-foreground">
            {item.label}
          </Link>
        </span>
      ))}
    </nav>
  );
}

type NotificationCenterProps = {
  notifications: DashboardNotification[];
};

function NotificationCenter({ notifications }: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const unseenCount = notifications.length;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((value) => !value)}
        className="relative inline-flex h-10 w-10 items-center justify-center rounded-md border border-border text-foreground transition-colors hover:bg-accent"
        aria-label="Toggle notifications"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0 1 18 14.158V11a6.002 6.002 0 0 0-4-5.659V5a2 2 0 1 0-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 1 1-6 0v-1m6 0H9" />
        </svg>
        {unseenCount > 0 && (
          <span className="absolute -right-1 -top-1 inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
            {unseenCount}
          </span>
        )}
      </button>
      {isOpen && (
        <div className="absolute right-0 z-40 mt-2 w-72 rounded-lg border border-border/60 bg-popover p-3 text-sm shadow-lg">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-semibold text-foreground">Notifications</span>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Close
            </button>
          </div>
          {notifications.length === 0 ? (
            <p className="text-xs text-muted-foreground">You're all caught up.</p>
          ) : (
            <ul className="space-y-2">
              {notifications.map((notification) => (
                <li key={notification.id} className={clsx("rounded-md px-3 py-2 text-xs", statusColor[notification.severity])}>
                  <p className="font-medium">{notification.title}</p>
                  <p className="text-xs opacity-80">{notification.description}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

