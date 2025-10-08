"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import {
  TwoFactorFormValues,
  twoFactorSchema,
} from "@/components/auth/schemas";

export type TwoFactorSubmitResult =
  | { status: "success" }
  | { status: "error"; message: string };

export type TwoFactorFormProps = {
  defaultValues?: Partial<TwoFactorFormValues>;
  onSubmit?: (values: TwoFactorFormValues) => Promise<TwoFactorSubmitResult>;
};

async function defaultSubmit(values: TwoFactorFormValues): Promise<TwoFactorSubmitResult> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ twoFactorToken: values.token }),
  });

  if (response.ok) {
    return { status: "success" };
  }

  const data = (await response.json()) as { message?: string };
  return { status: "error", message: data.message ?? "Invalid verification code" };
}

export function TwoFactorForm({ defaultValues, onSubmit }: TwoFactorFormProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<TwoFactorFormValues>({
    resolver: zodResolver(twoFactorSchema),
    defaultValues: {
      token: "",
      ...defaultValues,
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    setServerError(null);
    setIsSubmitting(true);

    try {
      const result = await (onSubmit ?? defaultSubmit)(values);

      if (result.status === "success") {
        form.reset();
      } else {
        setServerError(result.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  });

  return (
    <form className="space-y-6" onSubmit={handleSubmit} noValidate>
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Verify it&rsquo;s you</h1>
        <p className="text-sm text-muted-foreground">
          Enter the 6-digit code from your authenticator app to continue.
        </p>
      </div>

      <div className="space-y-2 text-left">
        <label className="text-sm font-medium text-foreground" htmlFor="token">
          One-time passcode
        </label>
        <input
          id="token"
          inputMode="numeric"
          autoComplete="one-time-code"
          className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-center text-lg tracking-[0.4em] shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          {...form.register("token")}
        />
        {form.formState.errors.token && (
          <p className="text-sm text-destructive">{form.formState.errors.token.message}</p>
        )}
      </div>

      {serverError && <p className="text-sm text-destructive">{serverError}</p>}

      <button
        type="submit"
        className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        disabled={isSubmitting}
      >
        {isSubmitting ? "Verifying…" : "Verify"}
      </button>
    </form>
  );
}
