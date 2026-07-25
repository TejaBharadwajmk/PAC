/**
 * BFF Proxy — POST /api/auth/logout
 * Clears the httpOnly refresh token and role cookies.
 */
import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.delete("pac_refresh_token");
  response.cookies.delete("pac_role");
  return response;
}
