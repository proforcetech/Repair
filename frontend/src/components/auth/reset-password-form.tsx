"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import {
  PasswordResetValues,
  passwordResetSchema,
} from "@/components/auth/schemas";

export type ResetPasswordSubmitResult =
  | { status: "success"; message?: string }
  | { status: "error"; message: string };

export type ResetPasswordFormProps = {
  defaultValues?: Partial<PasswordResetValues>;
  onSubmit?: (values: PasswordResetValues) => Promise<ResetPasswordSubmitResult>;
};

async function defaultSubmit(values: PasswordResetValues): Promise<ResetPasswordSubmitResult> {
  const response = await fetch("/api/auth/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });

  const data = (await response.json()) as { message?: string };

  if (response.ok) {
    return { status: "success", message: data.message };
  }

  return { status: "error", message: data.message ?? "Unable to reset password" };
}

export function ResetPasswordForm({ defaultValues, onSubmit }: ResetPasswordFormProps) {
  const [serverMessage, setServerMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<PasswordResetValues>({
    resolver: zodResolver(passwordResetSchema),
    defaultValues: {
      token: "",
      password: "",
      confirmPassword: "",
      ...defaultValues,
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    setServerMessage(null);
    setIsError(false);
    setIsSubmitting(true);

    try {
      const result = await (onSubmit ?? defaultSubmit)(values);

      if (result.status === "success") {
        setServerMessage(result.message ?? "Password updated successfully. You can close this tab.");
        form.reset();
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
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Reset password</h1>
        <p className="text-sm text-muted-foreground">
          Choose a strong password with at least one uppercase, lowercase, and number.
        </p>
      </div>

      <div className="space-y-5 text-left">
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground" htmlFor="reset-token">
            Reset token
          </label>
          <input
            id="reset-token"
            className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("token")}
          />
          {form.formState.errors.token && (
            <p className="text-sm text-destructive">{form.formState.errors.token.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground" htmlFor="new-password">
            New password
          </label>
          <input
            id="new-password"
            type="password"
            autoComplete="new-password"
            className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("password")}
          />
          {form.formState.errors.password && (
            <p className="text-sm text-destructive">{form.formState.errors.password.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground" htmlFor="confirm-password">
            Confirm password
          </label>
          <input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("confirmPassword")}
          />
          {form.formState.errors.confirmPassword && (
            <p className="text-sm text-destructive">{form.formState.errors.confirmPassword.message}</p>
          )}
        </div>
      </div>

      {serverMessage && (
        <p className={`text-sm ${isError ? "text-destructive" : "text-muted-foreground"}`}>{serverMessage}</p>
      )}

      <button
        type="submit"
        className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        disabled={isSubmitting}
      >
        {isSubmitting ? "Updating…" : "Update password"}
      </button>
    </form>
  );
}
