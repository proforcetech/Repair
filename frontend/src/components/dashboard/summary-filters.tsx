import { ChangeEvent } from "react";

import type { AdminSummaryFilters } from "@/services/dashboard";

export type TechnicianOption = { value: string; label: string };

type SummaryFiltersProps = {
  filters: AdminSummaryFilters;
  technicians: TechnicianOption[];
  onChange: (filters: AdminSummaryFilters) => void;
};

const jobStatuses = [
  "QUEUED",
  "IN_PROGRESS",
  "ON_HOLD",
  "COMPLETED",
];

export function SummaryFilters({ filters, technicians, onChange }: SummaryFiltersProps) {
  const handleStatusChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const next = event.target.value || undefined;
    onChange({ ...filters, status: next });
  };

  const handleTechnicianChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    onChange({ ...filters, technicianId: value || undefined });
  };

  const handleOverdueToggle = (event: ChangeEvent<HTMLInputElement>) => {
    onChange({ ...filters, overdueOnly: event.target.checked });
  };

  return (
    <div className="flex flex-wrap items-end gap-4">
      <label className="flex flex-col text-xs">
        <span className="mb-1 text-muted-foreground">Job status</span>
        <select
          value={filters.status ?? ""}
          onChange={handleStatusChange}
          className="min-w-[160px] rounded-md border border-border/70 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
        >
          <option value="">All statuses</option>
          {jobStatuses.map((status) => (
            <option key={status} value={status}>
              {status.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </label>
      {technicians.length > 0 && (
        <label className="flex flex-col text-xs">
          <span className="mb-1 text-muted-foreground">Technician</span>
          <select
            value={filters.technicianId ?? ""}
            onChange={handleTechnicianChange}
            className="min-w-[200px] rounded-md border border-border/70 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            <option value="">All technicians</option>
            {technicians.map((tech) => (
              <option key={tech.value} value={tech.value}>
                {tech.label}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
        <input
          type="checkbox"
          checked={Boolean(filters.overdueOnly)}
          onChange={handleOverdueToggle}
          className="h-4 w-4 rounded border-border/70 text-primary focus:ring-primary/40"
        />
        Overdue invoices only
      </label>
    </div>
  );
}
