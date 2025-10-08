"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import {
  LoginFormValues,
  loginSchema,
} from "@/components/auth/schemas";

export type LoginSubmitResult =
  | { status: "success" }
  | { status: "twoFactor"; message?: string }
  | { status: "error"; message: string; lockoutUntil?: string | null };

export type LoginFormProps = {
  defaultValues?: Partial<LoginFormValues>;
  onSubmit?: (values: LoginFormValues) => Promise<LoginSubmitResult>;
};

async function defaultSubmit(values: LoginFormValues): Promise<LoginSubmitResult> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });

  if (response.ok) {
    return { status: "success" };
  }

  const data = (await response.json()) as {
    message?: string;
    requiresTwoFactor?: boolean;
    lockoutUntil?: string | null;
  };

  if (data.requiresTwoFactor) {
    return { status: "twoFactor", message: data.message };
  }

  return {
    status: "error",
    message: data.message ?? "Unable to sign in",
    lockoutUntil: data.lockoutUntil ?? null,
  };
}

export function LoginForm({ defaultValues, onSubmit }: LoginFormProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const [lockoutUntil, setLockoutUntil] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      ...defaultValues,
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    setServerError(null);
    setLockoutUntil(null);
    setIsSubmitting(true);

    try {
      const result = await (onSubmit ?? defaultSubmit)(values);

      if (result.status === "success") {
        form.reset();
      } else if (result.status === "twoFactor") {
        setServerError(result.message ?? "Two-factor authentication required");
      } else {
        setServerError(result.message);
        if (result.lockoutUntil) {
          setLockoutUntil(result.lockoutUntil);
        }
      }

      return result;
    } finally {
      setIsSubmitting(false);
    }
  });

  return (
    <form className="space-y-6" onSubmit={handleSubmit} noValidate>
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Sign in</h1>
        <p className="text-sm text-muted-foreground">
          Enter your credentials to access the repair operations portal.
        </p>
      </div>

      <div className="space-y-5">
        <div className="space-y-2 text-left">
          <label className="text-sm font-medium text-foreground" htmlFor="email">
            Email address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("email")}
          />
          {form.formState.errors.email && (
            <p className="text-sm text-destructive">{form.formState.errors.email.message}</p>
          )}
        </div>

        <div className="space-y-2 text-left">
          <label className="text-sm font-medium text-foreground" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            {...form.register("password")}
          />
          {form.formState.errors.password && (
            <p className="text-sm text-destructive">{form.formState.errors.password.message}</p>
          )}
        </div>
      </div>

      {serverError && <p className="text-sm text-destructive">{serverError}</p>}
      {lockoutUntil && (
        <p className="text-sm text-warning">
          Account locked until {new Date(lockoutUntil).toLocaleString()}.
        </p>
      )}

      <button
        type="submit"
        className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        disabled={isSubmitting}
      >
        {isSubmitting ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
