"use client";

import { useMemo } from "react";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import type { Bay } from "@/services/bays";
import type { TechnicianUser } from "@/services/dashboard";

const staffBookingSchema = z.object({
  title: z.string().min(2, "Enter a descriptive title"),
  startTime: z.string().min(1, "Required"),
  endTime: z.string().min(1, "Required"),
  vehicleId: z.string().optional(),
  technicianId: z.string().optional(),
  bayId: z.string().optional(),
  reason: z.string().optional(),
});

const publicBookingSchema = staffBookingSchema.extend({
  customerId: z.string().min(1, "Customer ID is required"),
  vehicleId: z.string().min(1, "Vehicle ID is required"),
  reason: z.string().min(1, "Please describe the visit"),
});

export type StaffBookingValues = z.infer<typeof staffBookingSchema>;
export type PublicBookingValues = z.infer<typeof publicBookingSchema>;

type BookingFormsProps = {
  technicians: TechnicianUser[];
  bays: Bay[];
  onStaffSubmit: (values: StaffBookingValues) => Promise<void>;
  onPublicSubmit: (values: PublicBookingValues) => Promise<void>;
  staffPending?: boolean;
  publicPending?: boolean;
};

export function BookingForms({
  technicians,
  bays,
  onStaffSubmit,
  onPublicSubmit,
  staffPending,
  publicPending,
}: BookingFormsProps) {
  const technicianOptions = useMemo(() => technicians ?? [], [technicians]);
  const bayOptions = useMemo(() => bays ?? [], [bays]);

  const staffForm = useForm<StaffBookingValues>({
    resolver: zodResolver(staffBookingSchema),
    defaultValues: {
      title: "",
      startTime: "",
      endTime: "",
      vehicleId: "",
      technicianId: "",
      bayId: "",
      reason: "",
    },
  });

  const publicForm = useForm<PublicBookingValues>({
    resolver: zodResolver(publicBookingSchema),
    defaultValues: {
      title: "",
      startTime: "",
      endTime: "",
      technicianId: "",
      bayId: "",
      customerId: "",
      vehicleId: "",
      reason: "",
    },
  });

  const handleStaffSubmit = staffForm.handleSubmit(async (values) => {
    await onStaffSubmit(values);
    staffForm.reset();
  });

  const handlePublicSubmit = publicForm.handleSubmit(async (values) => {
    await onPublicSubmit(values);
    publicForm.reset();
  });

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <form onSubmit={handleStaffSubmit} className="space-y-4 rounded-lg border border-border/60 bg-card p-4 shadow-sm">
        <header className="space-y-1">
          <h2 className="text-lg font-semibold text-foreground">Staff booking</h2>
          <p className="text-sm text-muted-foreground">
            Create an appointment for a customer you are assisting directly from the counter.
          </p>
        </header>
        <Field label="Title" error={staffForm.formState.errors.title?.message}>
          <input
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...staffForm.register("title")}
          />
        </Field>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Start" error={staffForm.formState.errors.startTime?.message}>
            <input
              type="datetime-local"
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
              {...staffForm.register("startTime")}
            />
          </Field>
          <Field label="End" error={staffForm.formState.errors.endTime?.message}>
            <input
              type="datetime-local"
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
              {...staffForm.register("endTime")}
            />
          </Field>
        </div>
        <Field label="Vehicle ID" error={staffForm.formState.errors.vehicleId?.message}>
          <input
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
            {...staffForm.register("vehicleId")}
          />
        </Field>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Technician">
            <select
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
              {...staffForm.register("technicianId")}
            >
              <option value="">Unassigned</option>
              {technicianOptions.map((tech) => (
                <option key={tech.id} value={tech.id}>
                  {tech.email ?? tech.id}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Bay">
            <select
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
              {...staffForm.register("bayId")}
            >
              <option value="">Unassigned</option>
              {bayOptions.map((bay) => (
                <option key={bay.id} value={bay.id}>
                  {bay.name ?? bay.id}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Reason" error={staffForm.formState.errors.reason?.message}>
          <textarea
            rows={3}
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
            {...staffForm.register("reason")}
          />
        </Field>
        <div className="flex items-center justify-end gap-2">
          <button
            type="submit"
            disabled={staffPending}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {staffPending ? "Saving…" : "Create appointment"}
          </button>
        </div>
      </form>

      <form onSubmit={handlePublicSubmit} className="space-y-4 rounded-lg border border-border/60 bg-card p-4 shadow-sm">
        <header className="space-y-1">
          <h2 className="text-lg font-semibold text-foreground">Public booking</h2>
          <p className="text-sm text-muted-foreground">
            Capture a self-service booking from the website or kiosk with technician and bay preferences.
          </p>
        </header>
        <Field label="Title" error={publicForm.formState.errors.title?.message}>
          <input
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...publicForm.register("title")}
          />
        </Field>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Start" error={publicForm.formState.errors.startTime?.message}>
            <input
              type="datetime-local"
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
              {...publicForm.register("startTime")}
            />
          </Field>
          <Field label="End" error={publicForm.formState.errors.endTime?.message}>
            <input
              type="datetime-local"
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
              {...publicForm.register("endTime")}
            />
          </Field>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Customer ID" error={publicForm.formState.errors.customerId?.message}>
            <input
              type="text"
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
              {...publicForm.register("customerId")}
            />
          </Field>
          <Field label="Vehicle ID" error={publicForm.formState.errors.vehicleId?.message}>
            <input
              type="text"
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
              {...publicForm.register("vehicleId")}
            />
          </Field>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Technician">
            <select
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
              {...publicForm.register("technicianId")}
            >
              <option value="">Unassigned</option>
              {technicianOptions.map((tech) => (
                <option key={tech.id} value={tech.id}>
                  {tech.email ?? tech.id}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Bay">
            <select
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
              {...publicForm.register("bayId")}
            >
              <option value="">Unassigned</option>
              {bayOptions.map((bay) => (
                <option key={bay.id} value={bay.id}>
                  {bay.name ?? bay.id}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Reason" error={publicForm.formState.errors.reason?.message}>
          <textarea
            rows={3}
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm"
            {...publicForm.register("reason")}
          />
        </Field>
        <div className="flex items-center justify-end gap-2">
          <button
            type="submit"
            disabled={publicPending}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {publicPending ? "Submitting…" : "Book appointment"}
          </button>
        </div>
      </form>
    </div>
  );
}

type FieldProps = {
  label: string;
  error?: string;
  children: ReactNode;
};

function Field({ label, error, children }: FieldProps) {
  return (
    <label className="block space-y-1 text-sm">
      <span className="font-medium text-foreground">{label}</span>
      {children}
      {error ? <span className="text-xs text-destructive">{error}</span> : null}
    </label>
  );
}
