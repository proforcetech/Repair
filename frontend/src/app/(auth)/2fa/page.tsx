"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  TwoFactorForm,
  type TwoFactorSubmitResult,
} from "@/components/auth/two-factor-form";
import {
  clearPendingLogin,
  readPendingLogin,
  type PendingLoginPayload,
} from "@/components/auth/pending-login";

export default function TwoFactorPage() {
  const router = useRouter();
  const [pending, setPending] = useState<PendingLoginPayload | null>(null);

  useEffect(() => {
    setPending(readPendingLogin());
  }, []);

  const handleSubmit = async (values: { token: string }): Promise<TwoFactorSubmitResult> => {
    const latest = readPendingLogin();
    if (!latest) {
      return {
        status: "error",
        message: "Your login session expired. Please sign in again.",
      };
    }

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...latest, twoFactorToken: values.token }),
      });

      if (response.ok) {
        clearPendingLogin();
        router.replace("/");
        router.refresh();
        return { status: "success" };
      }

      const data = (await response.json().catch(() => ({}))) as { message?: string };
      return { status: "error", message: data.message ?? "Invalid verification code" };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unable to verify code",
      };
    }
  };

  if (!pending) {
    return (
      <div className="space-y-4 text-center text-sm text-muted-foreground">
        <p>The verification window expired. Restart your sign-in to continue.</p>
        <Link className="text-primary hover:underline" href="/login">
          Go back to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <TwoFactorForm onSubmit={handleSubmit} />
      <p className="text-center text-xs text-muted-foreground">
        Need to switch accounts?{" "}
        <Link className="text-primary hover:underline" href="/login">
          Use a different email
        </Link>
        .
      </p>
    </div>
  );
}
