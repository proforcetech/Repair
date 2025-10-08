"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import {
  CustomerUpdateValues,
  customerUpdateSchema,
} from "@/components/customers";
import {
  Customer,
  getCustomerSelf,
  updateCustomerSelf,
} from "@/services/customers";
import { showToast } from "@/stores/toast-store";

export default function CustomerProfilePage() {
  const queryClient = useQueryClient();
  const profileQuery = useQuery<Customer>({
    queryKey: ["portal", "profile"],
    queryFn: getCustomerSelf,
  });

  const mutation = useMutation({
    mutationFn: updateCustomerSelf,
    onSuccess: (response) => {
      queryClient.setQueryData(["portal", "profile"], response.customer);
      showToast({
        title: "Profile updated",
        description: "Your contact information has been saved.",
        variant: "success",
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

  const form = useForm<CustomerUpdateValues>({
    resolver: zodResolver(customerUpdateSchema),
    values: profileQuery.data
      ? {
          fullName: profileQuery.data.fullName,
          email: profileQuery.data.email,
          phone: profileQuery.data.phone,
          street: profileQuery.data.street ?? "",
          city: profileQuery.data.city ?? "",
          state: profileQuery.data.state ?? "",
          zip: profileQuery.data.zip ?? "",
        }
      : undefined,
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    await mutation.mutateAsync(values);
  });

  if (profileQuery.isLoading) {
    return <p className="text-sm text-muted-foreground">Loading your profile…</p>;
  }

  if (profileQuery.isError || !profileQuery.data) {
    return <p className="text-sm text-destructive">Unable to load your profile.</p>;
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">Your profile</h1>
        <p className="text-sm text-muted-foreground">
          Update your contact and mailing information. Changes apply immediately across the portal.
        </p>
      </header>

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
              className="w-full rounded-md border border-border/70 bg-muted px-3 py-2 text-sm shadow-sm"
              disabled
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
          <p className="text-sm text-muted-foreground">We use this information to confirm appointments and send updates.</p>
          <button
            type="submit"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Saving…" : "Save profile"}
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
    <label className="flex flex-col gap-2 text-sm">
      <span className="font-medium text-foreground">{label}</span>
      {children}
      {error && <span className="text-destructive">{error}</span>}
    </label>
  );
}
