"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { clsx } from "clsx";

const navigation = [
  { label: "Part catalog", href: "/inventory" },
  { label: "Stock transfers", href: "/inventory/transfers" },
  { label: "Purchase orders", href: "/inventory/purchase-orders" },
  { label: "Restock recommendations", href: "/inventory/restock" },
];

export default function InventoryLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border/60 bg-background/80 p-3">
        <nav className="flex flex-wrap gap-2">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "inline-flex items-center rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground shadow"
                    : "bg-muted/40 text-muted-foreground hover:bg-muted/60",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
      {children}
    </div>
  );
}
