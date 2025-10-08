"use client";

import { ReactNode, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import {
  VehicleFormValues,
  VehicleUpdateValues,
  vehicleSchema,
  vehicleUpdateSchema,
} from "@/components/customers/schemas";
import {
  Vehicle,
  VehicleCreateInput,
  VehicleUpdateInput,
  createVehicle,
  updateVehicle,
} from "@/services/customers";
import { showToast } from "@/stores/toast-store";

export type VehicleFormMode = "create" | "update";

export type VehicleFormProps = {
  mode?: VehicleFormMode;
  customerId?: string;
  vehicleId?: string;
  defaultValues?: Partial<VehicleFormValues>;
  onSuccess?: (vehicle: Vehicle) => void;
};

export function VehicleForm({
  mode = "create",
  customerId,
  vehicleId,
  defaultValues,
  onSuccess,
}: VehicleFormProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const form = useForm<VehicleFormValues | VehicleUpdateValues>({
    resolver: zodResolver(mode === "create" ? vehicleSchema : vehicleUpdateSchema),
    defaultValues: {
      vin: "",
      make: "",
      model: "",
      year: new Date().getFullYear(),
      ...defaultValues,
    },
  });

  const mutation = useMutation({
    mutationFn: async (values: VehicleFormValues | VehicleUpdateValues) => {
      const payload: VehicleCreateInput | VehicleUpdateInput = {
        ...values,
      };

      if (mode === "create") {
        if (!customerId) {
          throw new Error("Customer ID is required to create vehicles");
        }
        return createVehicle(customerId, payload as VehicleCreateInput);
      }

      if (!vehicleId) {
        throw new Error("Vehicle ID is required to update vehicles");
      }

      return updateVehicle(vehicleId, payload as VehicleUpdateInput);
    },
    onSuccess: (vehicle) => {
      showToast({
        title: mode === "create" ? "Vehicle added" : "Vehicle updated",
        description:
          mode === "create"
            ? `${vehicle.year} ${vehicle.make} ${vehicle.model} is now linked`
            : `${vehicle.year} ${vehicle.make} ${vehicle.model} saved`,
        variant: "success",
      });
      setServerError(null);
      if (customerId) {
        queryClient.invalidateQueries({ queryKey: ["customer", customerId, "vehicles"] });
      }
      onSuccess?.(vehicle);
      if (mode === "create") {
        form.reset({ vin: "", make: "", model: "", year: new Date().getFullYear() });
      } else {
        form.reset(vehicle as VehicleFormValues);
      }
    },
    onError: (error: unknown) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to save vehicle")
          : "Unable to save vehicle";
      setServerError(message);
      showToast({
        title: "Vehicle error",
        description: message,
        variant: "destructive",
      });
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    await mutation.mutateAsync({
      ...values,
      year:
        typeof values.year === "string"
          ? Number.parseInt(values.year, 10)
          : values.year,
    } as VehicleFormValues);
  });

  return (
    <form className="space-y-4" onSubmit={handleSubmit} noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="VIN" error={form.formState.errors.vin?.message}>
          <input
            id="vin"
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("vin")}
          />
        </Field>
        <Field label="Make" error={form.formState.errors.make?.message}>
          <input
            id="make"
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("make")}
          />
        </Field>
        <Field label="Model" error={form.formState.errors.model?.message}>
          <input
            id="model"
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("model")}
          />
        </Field>
        <Field label="Year" error={form.formState.errors.year?.message}>
          <input
            id="year"
            type="number"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("year", { valueAsNumber: true })}
          />
        </Field>
      </div>

      {serverError && <p className="text-sm text-destructive">{serverError}</p>}

      <button
        type="submit"
        className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        disabled={mutation.isPending}
      >
        {mutation.isPending
          ? mode === "create"
            ? "Adding…"
            : "Saving…"
          : mode === "create"
            ? "Add vehicle"
            : "Save vehicle"}
      </button>
    </form>
  );
}

type FieldProps = {
  label: string;
  error?: string;
  children: ReactNode;
};

function Field({ label, error, children }: FieldProps) {
  return (
    <label className="flex flex-col gap-2 text-sm">
      <span className="font-medium text-foreground">{label}</span>
      {children}
      {error && <span className="text-destructive">{error}</span>}
    </label>
  );
}
