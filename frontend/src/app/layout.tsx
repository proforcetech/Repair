import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ReactNode, Suspense } from "react";
import { clsx } from "clsx";

import { AppProviders } from "@/components/providers/app-providers";
import { AppShell } from "@/components/layout/app-shell";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
    title: "Repair Operations Portal",
    description: "Modern Auto Repair management UI powered by Next.js",
};

type RootLayoutProps = {
    children: ReactNode;
};

function LayoutFallback() {
    return (
        <div className="flex flex-col gap-4">
            <div className="h-9 w-1/3 animate-pulse rounded-md bg-muted" />
            <div className="grid gap-4 md:grid-cols-2">
                {Array.from({ length: 4 }).map((_, index) => (
                    <div key={index} className="h-32 animate-pulse rounded-lg bg-muted/70" />
                ))}
            </div>
        </div>
    );
}

export default function RootLayout({ children }: RootLayoutProps) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={clsx("min-h-screen bg-background text-foreground antialiased", inter.variable)}>
                <AppProviders>
                    <AppShell>
                        <Suspense fallback={<LayoutFallback />}>{children}</Suspense>
                    </AppShell>
                </AppProviders>
            </body>
        </html>
    );
}