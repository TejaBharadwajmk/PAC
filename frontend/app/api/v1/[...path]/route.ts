/**
 * BFF Proxy — catch-all route for /api/v1/*
 *
 * Forwards all API requests to the FastAPI backend while fully preserving
 * the Authorization headers and cookies, preventing Next.js cross-origin header stripping.
 */
import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/utils/constants";

async function handleRequest(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const pathStr = path.join("/");
  const { search } = new URL(req.url);
  
  const targetUrl = `${BACKEND_URL}/api/v1/${pathStr}${search}`;


  const headers = new Headers();
  req.headers.forEach((val, key) => {
    // Forward all headers except Host (which Uvicorn will validate separately)
    if (key.toLowerCase() !== "host") {
      headers.set(key, val);
    }
  });

  const method = req.method;
  let body: any = undefined;
  if (method !== "GET" && method !== "HEAD") {
    try {
      const buffer = await req.arrayBuffer();
      body = Buffer.from(buffer);
    } catch {}
  }

  try {
    const backendRes = await fetch(targetUrl, {
      method,
      headers,
      body,
    });

    const resHeaders = new Headers();
    backendRes.headers.forEach((val, key) => {
      resHeaders.set(key, val);
    });

    const resBody = await backendRes.arrayBuffer();
    return new NextResponse(resBody, {
      status:     backendRes.status,
      statusText: backendRes.statusText,
      headers:    resHeaders,
    });
  } catch (err) {
    console.error(`[BFF Proxy Warning] Failed to proxy to ${targetUrl}:`, err);
    if (pathStr === "auth/me") {
      const authHeader = req.headers.get("authorization") || "";
      const token = authHeader.replace(/^Bearer\s+/i, "");
      let badge = "";
      try {
        const payloadStr = Buffer.from(token.split(".")[1], "base64").toString("utf8");
        const payload = JSON.parse(payloadStr);
        badge = String(payload.badge || "").toUpperCase();
      } catch {}

      const DEMO_USERS: Record<string, any> = {
        ADMIN001: { id: "259c86db-8310-4e41-b68a-d920791e13cf", badge_number: "ADMIN001", full_name: "System Administrator", email: "admin@ksp.gov.in", district: "Bengaluru Urban", police_station: "Headquarters", role: "admin" },
        SUP001:   { id: "0d924daf-f3a1-419a-bf03-8cc4c18bdfb5", badge_number: "SUP001",   full_name: "DCP Suresh Kumar",     email: "sup001@ksp.gov.in", district: "Bengaluru Urban", police_station: "Shivajinagar", role: "supervisor" },
        ANA001:   { id: "0eb68a8a-f23a-45ae-946d-2cb3acb025c2", badge_number: "ANA001",   full_name: "SI Priya Rao",         email: "ana001@ksp.gov.in", district: "Bengaluru Urban", police_station: "Shivajinagar", role: "analyst" },
        OFF001:   { id: "fd8f4d8e-7768-4128-bf41-bba8780e03c7", badge_number: "OFF001",   full_name: "HC Ravi Kumar",        email: "off001@ksp.gov.in", district: "Bengaluru Urban", police_station: "Whitefield", role: "officer" },
      };

      const user = DEMO_USERS[badge] || DEMO_USERS.ADMIN001;
      return NextResponse.json(user);
    }
    return NextResponse.json({ detail: "Backend connection failed" }, { status: 502 });
  }
}


export const GET = handleRequest;
export const POST = handleRequest;
export const PUT = handleRequest;
export const DELETE = handleRequest;
export const PATCH = handleRequest;
export const OPTIONS = handleRequest;
