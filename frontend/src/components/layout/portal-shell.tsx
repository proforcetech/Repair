"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";

import { useSession } from "@/hooks/use-session";
import { useLayoutStore } from "@/stores/layout-store";

const navigation = [
  { label: "Dashboard", href: "/portal/dashboard" },
  { label: "Profile", href: "/portal/profile" },
  { label: "Warranty", href: "/portal/warranty" },
];

type PortalShellProps = {
  children: ReactNode;
};

export function PortalShell({ children }: PortalShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isSidebarOpen, toggleSidebar, closeSidebar } = useLayoutStore();
  const { user, isAuthenticated, role, isLoading } = useSession();

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || role !== "CUSTOMER")) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, role, router]);

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
            <Link href="/portal/dashboard" className="flex items-center gap-2 text-sm font-semibold">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground shadow">CP</span>
              <span className="hidden sm:inline">Customer Portal</span>
            </Link>
          </div>
          {isAuthenticated && (
            <div className="hidden flex-col text-xs leading-tight sm:flex">
              <span className="font-semibold text-foreground">{user?.email}</span>
              <span className="uppercase tracking-wide text-muted-foreground">{role}</span>
            </div>
          )}
        </div>
      </header>
      <div className="flex flex-1">
        <aside
          className={`fixed inset-y-0 left-0 z-30 w-60 border-r border-border/60 bg-background/95 px-4 py-6 transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${isSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
        >
          <nav className="space-y-1">
            {navigation.map((item) => {
              const isActive = pathname?.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={closeSidebar}
                  className={`flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary/10 text-primary shadow"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  }`}
                >
                  {item.label}
                  {isActive && <span className="inline-flex h-2 w-2 rounded-full bg-primary" />}
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
        <main className="flex-1 bg-gradient-to-b from-background to-background/95">
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
