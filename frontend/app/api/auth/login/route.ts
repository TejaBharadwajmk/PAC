/**
 * BFF Proxy — POST /api/auth/login
 *
 * Forwards badge+password credentials to the FastAPI backend.
 * On success: stores the refresh_token in an httpOnly cookie,
 * and sets pac_role cookie for Next.js middleware RBAC checking.
 */
import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/utils/constants";
import { jwtDecode } from "jwt-decode";

export async function POST(req: NextRequest) {
  const body = await req.json();

  let backendRes: Response;
  try {
    backendRes = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
  } catch {
    return NextResponse.json({ error: "Backend unreachable" }, { status: 503 });
  }

  if (!backendRes.ok) {
    const err = await backendRes.json().catch(() => ({ detail: "Authentication failed" }));
    return NextResponse.json(err, { status: backendRes.status });
  }

  const data = await backendRes.json() as {
    access_token: string;
    refresh_token: string;
    token_type:   string;
    expires_in:   number;
  };

  const response = NextResponse.json({
    access_token: data.access_token,
    expires_in:   data.expires_in,
    token_type:   data.token_type,
  });

  // Set the refresh token as an httpOnly cookie
  response.cookies.set("pac_refresh_token", data.refresh_token, {
    httpOnly: true,
    secure:   process.env.NODE_ENV === "production",
    sameSite: "lax",
    path:     "/",
    maxAge:   7 * 24 * 60 * 60, // 7 days
  });

  // Set pac_role cookie for middleware RBAC route guards
  try {
    const payload = jwtDecode<{ role?: string }>(data.access_token);
    if (payload.role) {
      response.cookies.set("pac_role", payload.role, {
        httpOnly: false,
        secure:   process.env.NODE_ENV === "production",
        sameSite: "lax",
        path:     "/",
        maxAge:   7 * 24 * 60 * 60,
      });
    }
  } catch {}

  return response;
}
