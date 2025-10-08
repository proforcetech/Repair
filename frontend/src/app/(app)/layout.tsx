import { ReactNode, Suspense } from "react";

import { AppShell } from "@/components/layout/app-shell";

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

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AppShell>
      <Suspense fallback={<LayoutFallback />}>{children}</Suspense>
    </AppShell>
  );
}
