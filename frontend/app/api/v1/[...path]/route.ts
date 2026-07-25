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
    console.error(`[BFF Proxy Error] Failed to proxy to ${targetUrl}:`, err);
    return NextResponse.json({ detail: "Backend connection failed" }, { status: 502 });
  }
}

export const GET = handleRequest;
export const POST = handleRequest;
export const PUT = handleRequest;
export const DELETE = handleRequest;
export const PATCH = handleRequest;
export const OPTIONS = handleRequest;
