"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import {
  PasswordResetRequestValues,
  passwordResetRequestSchema,
} from "@/components/auth/schemas";

export type ForgotPasswordSubmitResult =
  | { status: "success"; message?: string }
  | { status: "error"; message: string };

export type ForgotPasswordFormProps = {
  onSubmit?: (values: PasswordResetRequestValues) => Promise<ForgotPasswordSubmitResult>;
};

async function defaultSubmit(
  values: PasswordResetRequestValues,
): Promise<ForgotPasswordSubmitResult> {
  const response = await fetch("/api/auth/request-password-reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });

  const data = (await response.json()) as { message?: string };

  if (response.ok) {
    return { status: "success", message: data.message };
  }

  return { status: "error", message: data.message ?? "Unable to process request" };
}

export function ForgotPasswordForm({ onSubmit }: ForgotPasswordFormProps) {
  const [serverMessage, setServerMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<PasswordResetRequestValues>({
    resolver: zodResolver(passwordResetRequestSchema),
    defaultValues: { email: "" },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    setServerMessage(null);
    setIsError(false);
    setIsSubmitting(true);

    try {
      const result = await (onSubmit ?? defaultSubmit)(values);

      if (result.status === "success") {
        form.reset();
        setServerMessage(result.message ?? "If that email exists we sent a reset link.");
        setIsError(false);
      } else {
        setServerMessage(result.message);
        setIsError(true);
      }
    } finally {
      setIsSubmitting(false);
    }
  });

  return (
    <form className="space-y-6" onSubmit={handleSubmit} noValidate>
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Forgot password</h1>
        <p className="text-sm text-muted-foreground">
          We&rsquo;ll email a password reset link if the address is registered.
        </p>
      </div>

      <div className="space-y-2 text-left">
        <label className="text-sm font-medium text-foreground" htmlFor="reset-email">
          Email address
        </label>
        <input
          id="reset-email"
          type="email"
          autoComplete="email"
          className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          {...form.register("email")}
        />
        {form.formState.errors.email && (
          <p className="text-sm text-destructive">{form.formState.errors.email.message}</p>
        )}
      </div>

      {serverMessage && (
        <p className={`text-sm ${isError ? "text-destructive" : "text-muted-foreground"}`}>{serverMessage}</p>
      )}

      <button
        type="submit"
        className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        disabled={isSubmitting}
      >
        {isSubmitting ? "Sending…" : "Send reset link"}
      </button>
    </form>
  );
}
