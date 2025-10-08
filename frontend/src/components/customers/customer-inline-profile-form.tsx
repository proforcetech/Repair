"use client";

import { ReactNode, useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import {
  CustomerUpdateValues,
  customerUpdateSchema,
} from "@/components/customers/schemas";
import { Customer, updateCustomer } from "@/services/customers";
import { showToast } from "@/stores/toast-store";

export type CustomerInlineProfileFormProps = {
  customerId: string;
  customer: Customer;
  onCustomerUpdated?: (customer: Customer) => void;
};

export function CustomerInlineProfileForm({
  customerId,
  customer,
  onCustomerUpdated,
}: CustomerInlineProfileFormProps) {
  const queryClient = useQueryClient();

  const form = useForm<CustomerUpdateValues>({
    resolver: zodResolver(customerUpdateSchema),
    defaultValues: {
      fullName: customer.fullName,
      email: customer.email,
      phone: customer.phone,
      street: customer.street ?? "",
      city: customer.city ?? "",
      state: customer.state ?? "",
      zip: customer.zip ?? "",
    },
  });

  useEffect(() => {
    form.reset({
      fullName: customer.fullName,
      email: customer.email,
      phone: customer.phone,
      street: customer.street ?? "",
      city: customer.city ?? "",
      state: customer.state ?? "",
      zip: customer.zip ?? "",
    });
  }, [customer, form]);

  const mutation = useMutation({
    mutationFn: async (values: CustomerUpdateValues) => {
      const payload = {
        ...values,
        street: values.street?.trim() ? values.street : undefined,
        city: values.city?.trim() ? values.city : undefined,
        state: values.state?.trim() ? values.state : undefined,
        zip: values.zip?.trim() ? values.zip : undefined,
      };
      return updateCustomer(customerId, payload);
    },
    onSuccess: (updated) => {
      showToast({
        title: "Profile updated",
        description: `${updated.fullName}'s profile is up to date.`,
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: ["customer", customerId] });
      onCustomerUpdated?.(updated);
      form.reset({
        fullName: updated.fullName,
        email: updated.email,
        phone: updated.phone,
        street: updated.street ?? "",
        city: updated.city ?? "",
        state: updated.state ?? "",
        zip: updated.zip ?? "",
      });
    },
    onError: (error: unknown) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to update profile")
          : "Unable to update profile";
      showToast({
        title: "Update failed",
        description: message,
        variant: "destructive",
      });
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    await mutation.mutateAsync(values);
  });

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Full name" error={form.formState.errors.fullName?.message}>
          <input
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("fullName")}
          />
        </Field>
        <Field label="Email" error={form.formState.errors.email?.message}>
          <input
            type="email"
            disabled
            className="w-full rounded-md border border-border/70 bg-muted px-3 py-2 text-sm shadow-sm"
            {...form.register("email")}
          />
        </Field>
        <Field label="Phone" error={form.formState.errors.phone?.message}>
          <input
            type="tel"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("phone")}
          />
        </Field>
        <Field label="Street" error={form.formState.errors.street?.message}>
          <input
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("street")}
          />
        </Field>
        <Field label="City" error={form.formState.errors.city?.message}>
          <input
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("city")}
          />
        </Field>
        <Field label="State" error={form.formState.errors.state?.message}>
          <input
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("state")}
          />
        </Field>
        <Field label="ZIP" error={form.formState.errors.zip?.message}>
          <input
            type="text"
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("zip")}
          />
        </Field>
      </div>
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          Changes are saved inline. Edit the fields above and click save.
        </p>
        <button
          type="submit"
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? "Saving…" : "Save profile"}
        </button>
      </div>
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
