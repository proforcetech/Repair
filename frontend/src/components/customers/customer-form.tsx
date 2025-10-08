"use client";

import { ReactNode, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import {
  CustomerFormValues,
  customerCreateSchema,
  customerUpdateSchema,
  CustomerUpdateValues,
} from "@/components/customers/schemas";
import {
  Customer,
  CustomerCreateInput,
  CustomerUpdateInput,
  createCustomer,
  updateCustomer,
} from "@/services/customers";
import { showToast } from "@/stores/toast-store";

export type CustomerFormMode = "create" | "update";

export type CustomerFormProps = {
  mode?: CustomerFormMode;
  customerId?: string;
  defaultValues?: Partial<CustomerFormValues>;
  onSuccess?: (customer: Customer) => void;
};

export function CustomerForm({
  mode = "create",
  customerId,
  defaultValues,
  onSuccess,
}: CustomerFormProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const form = useForm<CustomerFormValues | CustomerUpdateValues>({
    resolver: zodResolver(mode === "create" ? customerCreateSchema : customerUpdateSchema),
    defaultValues: {
      fullName: "",
      email: "",
      phone: "",
      street: "",
      city: "",
      state: "",
      zip: "",
      ...defaultValues,
    },
  });

  const mutation = useMutation({
    mutationFn: async (values: CustomerFormValues | CustomerUpdateValues) => {
      const payload: CustomerCreateInput | CustomerUpdateInput = {
        ...values,
        street: values.street ?? undefined,
        city: values.city ?? undefined,
        state: values.state ?? undefined,
        zip: values.zip ?? undefined,
      };

      if (mode === "create") {
        return createCustomer(payload as CustomerCreateInput);
      }

      if (!customerId) {
        throw new Error("Customer ID is required for updates");
      }

      return updateCustomer(customerId, payload as CustomerUpdateInput);
    },
    onSuccess: (customer) => {
      setServerError(null);
      showToast({
        title: mode === "create" ? "Customer created" : "Customer updated",
        description:
          mode === "create"
            ? `Successfully added ${customer.fullName}`
            : `${customer.fullName}'s profile was updated`,
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      if (customerId) {
        queryClient.invalidateQueries({ queryKey: ["customer", customerId] });
      }
      onSuccess?.(customer);
      if (mode === "create") {
        form.reset();
      } else {
        form.reset(customer as CustomerFormValues);
      }
    },
    onError: (error: unknown) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to save customer")
          : "Unable to save customer";
      setServerError(message);
      showToast({
        title: "Save failed",
        description: message,
        variant: "destructive",
      });
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    await mutation.mutateAsync(values);
  });

  return (
    <form className="space-y-4" onSubmit={handleSubmit} noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Full name" error={form.formState.errors.fullName?.message}>
          <input
            id="fullName"
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("fullName")}
          />
        </Field>
        <Field label="Email" error={form.formState.errors.email?.message}>
          <input
            id="email"
            type="email"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("email")}
            disabled={mode === "update"}
          />
        </Field>
        <Field label="Phone" error={form.formState.errors.phone?.message}>
          <input
            id="phone"
            type="tel"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("phone")}
          />
        </Field>
        <Field label="Street" error={form.formState.errors.street?.message}>
          <input
            id="street"
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("street")}
          />
        </Field>
        <Field label="City" error={form.formState.errors.city?.message}>
          <input
            id="city"
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("city")}
          />
        </Field>
        <Field label="State" error={form.formState.errors.state?.message}>
          <input
            id="state"
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("state")}
          />
        </Field>
        <Field label="ZIP" error={form.formState.errors.zip?.message}>
          <input
            id="zip"
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("zip")}
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
            ? "Creating…"
            : "Saving…"
          : mode === "create"
            ? "Create customer"
            : "Save changes"}
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
