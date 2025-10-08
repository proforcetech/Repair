import { NextRequest, NextResponse } from "next/server";

import { resetPassword } from "@/services/auth";

interface ResetPasswordBody {
  token?: string;
  password?: string;
}

export async function POST(request: NextRequest) {
  const body = (await request.json()) as ResetPasswordBody;

  if (!body.token || !body.password) {
    return NextResponse.json(
      { success: false, message: "Token and password are required" },
      { status: 400 },
    );
  }

  try {
    const data = await resetPassword({ token: body.token, password: body.password });
    return NextResponse.json({ success: true, ...data });
  } catch (error) {
    const status = typeof (error as { status?: number })?.status === "number" ? (error as { status?: number }).status : 400;
    const message = error instanceof Error ? error.message : "Unable to reset password";
    return NextResponse.json({ success: false, message }, { status });
  }
}
