import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ReactNode } from "react";
import { clsx } from "clsx";

import { AppProviders } from "@/components/providers/app-providers";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
    title: "Repair Operations Portal",
    description: "Modern Auto Repair management UI powered by Next.js",
};

type RootLayoutProps = {
    children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={clsx("min-h-screen bg-background text-foreground antialiased", inter.variable)}>
                <AppProviders>{children}</AppProviders>
            </body>
        </html>
    );
}