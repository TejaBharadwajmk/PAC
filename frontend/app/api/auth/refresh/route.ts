/**
 * BFF Proxy — POST /api/auth/refresh
 *
 * Reads the pac_refresh_token httpOnly cookie and exchanges it
 * for a new access_token from the FastAPI backend. Updates pac_role cookie.
 */
import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/utils/constants";
import { jwtDecode } from "jwt-decode";

export async function POST(req: NextRequest) {
  const refreshToken = req.cookies.get("pac_refresh_token")?.value;

  if (!refreshToken) {
    return NextResponse.json({ error: "No refresh token" }, { status: 401 });
  }

  let backendRes: Response;
  try {
    backendRes = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    return NextResponse.json({ error: "Backend unreachable" }, { status: 503 });
  }

  if (!backendRes.ok) {
    // Refresh failed — clear the stale cookies
    const response = NextResponse.json({ error: "Session expired" }, { status: 401 });
    response.cookies.delete("pac_refresh_token");
    response.cookies.delete("pac_role");
    return response;
  }

  const data = await backendRes.json() as {
    access_token: string;
    refresh_token: string;
    expires_in:   number;
  };

  const response = NextResponse.json({
    access_token: data.access_token,
    expires_in:   data.expires_in,
  });

  // Rotate the refresh token
  response.cookies.set("pac_refresh_token", data.refresh_token, {
    httpOnly: true,
    secure:   process.env.NODE_ENV === "production",
    sameSite: "lax",
    path:     "/",
    maxAge:   7 * 24 * 60 * 60,
  });

  // Update pac_role cookie
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
