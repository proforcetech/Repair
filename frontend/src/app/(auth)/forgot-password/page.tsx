"use client";

import Link from "next/link";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";

export default function ForgotPasswordPage() {
  return (
    <div className="space-y-6">
      <ForgotPasswordForm />
      <div className="text-center text-sm">
        <Link className="text-primary hover:underline" href="/login">
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
