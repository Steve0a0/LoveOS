import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL;

const PROTECTED_PATHS = [
  "/dashboard",
  "/notes",
  "/timeline",
  "/dates",
  "/safe-check",
  "/live-location",
  "/settings",
  "/pair",
  "/invite",
];

const AUTH_PATHS = ["/login", "/signup"];

export function middleware(request) {
  const { pathname } = request.nextUrl;

  // Proxy /api/* to Django backend
  if (pathname.startsWith("/api/")) {
    // Ensure trailing slash for Django
    const backendPath = pathname.endsWith("/") ? pathname : pathname + "/";
    const target = new URL(backendPath, BACKEND_URL);
    target.search = request.nextUrl.search;
    return NextResponse.rewrite(target);
  }

  const hasToken = request.cookies.has("auth_token");

  // Redirect authenticated users away from auth pages
  if (AUTH_PATHS.some((p) => pathname.startsWith(p)) && hasToken) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // Redirect unauthenticated users to login
  if (PROTECTED_PATHS.some((p) => pathname.startsWith(p)) && !hasToken) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/api/:path*",
    "/dashboard/:path*",
    "/notes/:path*",
    "/timeline/:path*",
    "/dates/:path*",
    "/safe-check/:path*",
    "/live-location/:path*",
    "/settings/:path*",
    "/pair/:path*",
    "/invite/:path*",
    "/login",
    "/signup",
  ],
};
