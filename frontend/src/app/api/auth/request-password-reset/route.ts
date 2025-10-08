import { NextRequest, NextResponse } from "next/server";

import { requestPasswordReset } from "@/services/auth";

interface PasswordResetRequestBody {
  email?: string;
}

export async function POST(request: NextRequest) {
  const body = (await request.json()) as PasswordResetRequestBody;

  if (!body.email) {
    return NextResponse.json(
      { success: false, message: "Email address is required" },
      { status: 400 },
    );
  }

  try {
    const data = await requestPasswordReset({ email: body.email });
    return NextResponse.json({ success: true, ...data });
  } catch (error) {
    const status = typeof (error as { status?: number })?.status === "number" ? (error as { status?: number }).status : 500;
    const message = error instanceof Error ? error.message : "Unable to send reset link";
    return NextResponse.json({ success: false, message }, { status });
  }
}
