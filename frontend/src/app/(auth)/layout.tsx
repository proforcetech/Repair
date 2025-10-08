import { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/20 p-6">
      <div className="w-full max-w-md space-y-6 rounded-2xl border border-border/60 bg-background/95 p-8 shadow-xl backdrop-blur">
        {children}
      </div>
    </div>
  );
}
