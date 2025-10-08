"use client";

import { startTransition } from "react";

import { showToast } from "@/stores/toast-store";

const actions = [
  {
    label: "Schedule appointment",
    description: "Book the next available bay and technician.",
    variant: "success" as const,
  },
  {
    label: "Generate estimate",
    description: "Draft a repair estimate using saved templates.",
    variant: "default" as const,
  },
  {
    label: "Flag quality issue",
    description: "Send a quick follow-up to the inspection team.",
    variant: "warning" as const,
  },
];

export function QuickActions() {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {actions.map((action) => (
        <button
          key={action.label}
          type="button"
          onClick={() =>
            startTransition(() => {
              showToast({
                title: action.label,
                description: action.description,
                variant: action.variant,
              });
            })
          }
          className="group flex flex-col gap-1 rounded-lg border border-border/70 bg-background px-4 py-3 text-left shadow-sm transition-colors hover:border-primary/60 hover:bg-accent/40"
        >
          <span className="flex items-center justify-between text-sm font-semibold text-foreground">
            {action.label}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="h-4 w-4 opacity-60 transition-transform group-hover:translate-x-1"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="m9 5 7 7-7 7" />
            </svg>
          </span>
          <span className="text-xs text-muted-foreground">{action.description}</span>
        </button>
      ))}
    </div>
  );
}