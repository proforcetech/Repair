"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo } from "react";

import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const token = useMemo(() => searchParams.get("token") ?? "", [searchParams]);

  return (
    <div className="space-y-6">
      <ResetPasswordForm defaultValues={{ token }} />
      <div className="text-center text-sm">
        <Link className="text-primary hover:underline" href="/login">
          Return to sign in
        </Link>
      </div>
    </div>
  );
}
