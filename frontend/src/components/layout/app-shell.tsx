"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useState } from "react";
import { clsx } from "clsx";

import { useLayoutStore } from "@/stores/layout-store";
import { useSession } from "@/hooks/use-session";

const navigation = [
    { label: "Dashboard", href: "/" },
    { label: "Work Orders", href: "/work-orders" },
    { label: "Technicians", href: "/technicians" },
    { label: "Inventory", href: "/inventory" },
];

type AppShellProps = {
    children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
    const pathname = usePathname();
    const router = useRouter();
    const { isSidebarOpen, toggleSidebar, closeSidebar } = useLayoutStore();
    const { user, isAuthenticated } = useSession();
    const [isSigningOut, setIsSigningOut] = useState(false);

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

    const NavItems = () => (
        <nav className="flex flex-col gap-1">
            {navigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        onClick={closeSidebar}
                        className={clsx(
                            "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                            isActive
                                ? "bg-primary/10 text-primary shadow-brand"
                                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                        )}
                    >
                        {item.label}
                    </Link>
                );
            })}
        </nav>
    );

    return (
        <div className="flex min-h-screen flex-col">
            <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur">
                <div className="container flex h-16 items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border text-foreground transition-colors hover:bg-accent lg:hidden"
                            onClick={toggleSidebar}
                            aria-label="Toggle navigation"
                        >
                            <span className="sr-only">Toggle navigation</span>
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                className="h-5 w-5"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 12h16M4 17h16" />
                            </svg>
                        </button>
                        <Link href="/" className="flex items-center gap-2 font-semibold text-foreground">
                            <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-brand">
                                AR
                            </span>
                            <span className="hidden text-lg tracking-tight sm:inline">Auto Repair Portal</span>
                        </Link>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="hidden items-center gap-2 lg:flex">
                            <NavItems />
                        </div>
                        {isAuthenticated ? (
                            <div className="flex items-center gap-2">
                                <div className="hidden text-right text-xs leading-tight sm:block">
                                    <p className="font-semibold text-foreground">{user?.email}</p>
                                    <p className="uppercase tracking-wide text-muted-foreground">{user?.role}</p>
                                </div>
                                <button
                                    type="button"
                                    onClick={handleSignOut}
                                    className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
                                    disabled={isSigningOut}
                                >
                                    {isSigningOut ? "Signing out…" : "Sign out"}
                                </button>
                            </div>
                        ) : (
                            <Link
                                href="/login"
                                className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
                            >
                                Sign in
                            </Link>
                        )}
                    </div>
                </div>
            </header>

            <div className="flex flex-1">
                <aside
                    className={clsx(
                        "fixed inset-y-0 left-0 z-30 w-64 border-r border-border/70 bg-background/95 px-4 py-6 transition-transform duration-300 ease-in-out lg:static lg:translate-x-0",
                        isSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
                    )}
                >
                    <div className="hidden lg:block">
                        <NavItems />
                    </div>
                    <div className="lg:hidden">
                        <div className="mb-6 flex items-center justify-between">
                            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Navigation</h2>
                            <button
                                type="button"
                                onClick={closeSidebar}
                                className="rounded-md border border-border p-2 text-muted-foreground hover:bg-accent"
                            >
                                <span className="sr-only">Close navigation</span>
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    className="h-4 w-4"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" d="m16 8-8 8m0-8 8 8" />
                                </svg>
                            </button>
                        </div>
                        <NavItems />
                    </div>
                </aside>
                {isSidebarOpen && (
                    <button
                        type="button"
                        className="fixed inset-0 z-20 bg-black/40 backdrop-blur-sm lg:hidden"
                        onClick={closeSidebar}
                        aria-label="Close sidebar overlay"
                    />
                )}
                <main className="flex-1 bg-gradient-to-b from-background to-background/90">
                    <div className="container py-8">
                        <div className="rounded-xl border border-border/70 bg-card/80 p-6 shadow-sm backdrop-blur">
                            {children}
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}