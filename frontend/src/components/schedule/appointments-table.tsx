"use client";

import { useMemo } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { format } from "date-fns";

import type { Appointment } from "@/services/appointments";

type AppointmentsTableProps = {
  appointments: Appointment[];
  isLoading?: boolean;
  remindersInFlight: Set<string>;
  syncInFlight: Set<string>;
  onSendReminder: (appointmentId: string) => void;
  onSync: (appointmentId: string) => void;
};

export function AppointmentsTable({
  appointments,
  isLoading,
  remindersInFlight,
  syncInFlight,
  onSendReminder,
  onSync,
}: AppointmentsTableProps) {
  const columns = useMemo<ColumnDef<Appointment>[]>(
    () => [
      {
        accessorKey: "title",
        header: "Title",
        cell: (info) => (
          <span className="font-medium text-foreground">{info.getValue<string>()}</span>
        ),
      },
      {
        accessorKey: "startTime",
        header: "Start",
        cell: (info) => {
          const value = info.getValue<string>();
          const date = value ? new Date(value) : undefined;
          return (
            <time className="text-sm text-muted-foreground" dateTime={value}>
              {date ? format(date, "MMM d, yyyy h:mm a") : "—"}
            </time>
          );
        },
      },
      {
        accessorKey: "endTime",
        header: "End",
        cell: (info) => {
          const value = info.getValue<string>();
          const date = value ? new Date(value) : undefined;
          return (
            <time className="text-sm text-muted-foreground" dateTime={value}>
              {date ? format(date, "MMM d, yyyy h:mm a") : "—"}
            </time>
          );
        },
      },
      {
        accessorKey: "technicianId",
        header: "Technician",
        cell: (info) => info.getValue<string>() || "Unassigned",
      },
      {
        accessorKey: "bayId",
        header: "Bay",
        cell: (info) => info.getValue<string>() || "Unassigned",
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => {
          const appointmentId = row.original.id;
          const reminderPending = remindersInFlight.has(appointmentId);
          const syncPending = syncInFlight.has(appointmentId);

          return (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => onSendReminder(appointmentId)}
                disabled={reminderPending}
                className="rounded-md border border-border/70 px-2 py-1 text-xs font-medium text-foreground transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
              >
                {reminderPending ? "Sending…" : "Send reminder"}
              </button>
              <button
                type="button"
                onClick={() => onSync(appointmentId)}
                disabled={syncPending}
                className="rounded-md border border-border/70 px-2 py-1 text-xs font-medium text-foreground transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
              >
                {syncPending ? "Syncing…" : "Sync calendar"}
              </button>
            </div>
          );
        },
      },
    ],
    [onSendReminder, onSync, remindersInFlight, syncInFlight],
  );

  const table = useReactTable({
    data: appointments,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="rounded-lg border border-border/60 bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
        <h2 className="text-lg font-semibold text-foreground">Upcoming appointments</h2>
        {isLoading ? (
          <span className="text-xs text-muted-foreground">Loading…</span>
        ) : (
          <span className="text-xs text-muted-foreground">{appointments.length} total</span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border/60 text-sm">
          <thead className="bg-muted/40">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    scope="col"
                    className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-border/60 bg-card">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-6 text-center text-sm text-muted-foreground">
                  {isLoading ? "Loading appointments…" : "No appointments found for the selected filters."}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-muted/40">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="whitespace-nowrap px-4 py-3">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
