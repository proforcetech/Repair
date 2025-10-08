"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { LoginForm, type LoginSubmitResult } from "@/components/auth/login-form";
import { clearPendingLogin, savePendingLogin } from "@/components/auth/pending-login";

type LoginResponse = {
  message?: string;
  requiresTwoFactor?: boolean;
  lockoutUntil?: string | null;
};

async function authenticate(values: { email: string; password: string }): Promise<{
  response: Response;
  body: LoginResponse;
}> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });

  const body = (await response.json().catch(() => ({}))) as LoginResponse;
  return { response, body };
}

export default function LoginPage() {
  const router = useRouter();

  const handleSubmit = async (values: { email: string; password: string }): Promise<LoginSubmitResult> => {
    try {
      const { response, body } = await authenticate(values);

      if (response.ok) {
        clearPendingLogin();
        router.replace("/");
        router.refresh();
        return { status: "success" };
      }

      if (body.requiresTwoFactor) {
        savePendingLogin(values);
        router.push("/2fa");
        return { status: "twoFactor", message: body.message };
      }

      return {
        status: "error",
        message: body.message ?? "Unable to sign in",
        lockoutUntil: body.lockoutUntil ?? null,
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unable to sign in",
      };
    }
  };

  return (
    <div className="space-y-6">
      <LoginForm onSubmit={handleSubmit} />
      <div className="text-center text-sm">
        <Link className="text-primary hover:underline" href="/forgot-password">
          Forgot your password?
        </Link>
      </div>
    </div>
  );
}
