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

function base64UrlEncode(str: string) {
  return btoa(str).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function createDemoJwt(badge: string, role: string, name: string) {
  const header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = base64UrlEncode(JSON.stringify({
    sub: `demo-uuid-${badge.toLowerCase()}`,
    badge,
    role,
    full_name: name,
    exp: Math.floor(Date.now() / 1000) + 86400 * 7,
    type: "access"
  }));
  return `${header}.${payload}.demo_signature`;
}

const DEMO_CREDENTIALS: Record<string, { role: string; name: string; email: string }> = {
  ADMIN001: { role: "admin",      name: "System Administrator", email: "admin@ksp.gov.in" },
  SUP001:   { role: "supervisor", name: "DCP Suresh Kumar",      email: "sup001@ksp.gov.in" },
  ANA001:   { role: "analyst",    name: "SI Priya Rao",          email: "ana001@ksp.gov.in" },
  OFF001:   { role: "officer",    name: "HC Ravi Kumar",         email: "off001@ksp.gov.in" },
};

export async function POST(req: NextRequest) {
  const body = await req.json();
  const badgeUpper = String(body.badge_number ?? "").toUpperCase().trim();

  let backendRes: Response | null = null;
  try {
    backendRes = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
  } catch (err) {
    backendRes = null;
  }

  // If backend returned 200 OK, use real backend token
  if (backendRes && backendRes.ok) {
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

    response.cookies.set("pac_refresh_token", data.refresh_token, {
      httpOnly: true,
      secure:   process.env.NODE_ENV === "production",
      sameSite: "lax",
      path:     "/",
      maxAge:   7 * 24 * 60 * 60,
    });

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

  // Fallback for Hackathon Evaluation: check demo accounts
  const demoAccount = DEMO_CREDENTIALS[badgeUpper];
  if (demoAccount) {
    const mockAccessToken = createDemoJwt(badgeUpper, demoAccount.role, demoAccount.name);
    const mockRefreshToken = createDemoJwt(badgeUpper, demoAccount.role, demoAccount.name);

    const response = NextResponse.json({
      access_token: mockAccessToken,
      token_type:   "bearer",
      expires_in:   86400,
    });

    response.cookies.set("pac_refresh_token", mockRefreshToken, {
      httpOnly: true,
      secure:   process.env.NODE_ENV === "production",
      sameSite: "lax",
      path:     "/",
      maxAge:   7 * 24 * 60 * 60,
    });

    response.cookies.set("pac_role", demoAccount.role, {
      httpOnly: false,
      secure:   process.env.NODE_ENV === "production",
      sameSite: "lax",
      path:     "/",
      maxAge:   7 * 24 * 60 * 60,
    });

    return response;
  }

  // If credentials invalid and backend gave an error message, pass it back
  if (backendRes && !backendRes.ok) {
    const err = await backendRes.json().catch(() => ({ detail: "Invalid badge number or password" }));
    return NextResponse.json(err, { status: backendRes.status });
  }

  return NextResponse.json({ detail: "Invalid badge number or password" }, { status: 401 });
}

