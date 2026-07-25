/**
 * PAC — Next.js Proxy (Route Protection)
 *
 * Protects all dashboard routes by checking:
 * 1. Presence of pac_refresh_token cookie (proxy for a valid session).
 * 2. Role-based route protection for admin-only and analyst-only paths.
 */

import { NextRequest, NextResponse } from "next/server";

const PROTECTED_PATHS = [
  "/crimes",
  "/criminals",
  "/dna",
  "/geo",
  "/network",
  "/assistant",
  "/predictions",
  "/reports",
  "/admin",
];

const ADMIN_ONLY_PATHS = ["/admin"];
const ANALYST_AND_ABOVE_PATHS = ["/dna", "/geo", "/network", "/predictions"];

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const refreshToken = request.cookies.get("pac_refresh_token")?.value;
  const role = request.cookies.get("pac_role")?.value ?? "";

  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p));
  if (!isProtected) return NextResponse.next();

  if (!refreshToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  const isAdminOnly = ADMIN_ONLY_PATHS.some((p) => pathname.startsWith(p));
  if (isAdminOnly && role !== "admin" && role !== "supervisor" && role !== "") {
    return NextResponse.redirect(new URL("/unauthorized", request.url));
  }

  const isAnalystOnly = ANALYST_AND_ABOVE_PATHS.some((p) => pathname.startsWith(p));
  if (isAnalystOnly && role === "officer") {
    return NextResponse.redirect(new URL("/unauthorized", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|login|unauthorized|api).*)",
  ],
};
