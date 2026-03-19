const BACKEND_URL = process.env.BACKEND_URL;

async function handler(request, { params }) {
  const { path } = await params;
  const targetPath = path.join("/");
  const url = new URL(request.url);
  // Preserve trailing slash to avoid Django APPEND_SLASH redirect loops
  const hasTrailingSlash = url.pathname.endsWith("/");
  const target = `${BACKEND_URL}/api/${targetPath}${hasTrailingSlash ? "/" : ""}${url.search}`;

  const headers = new Headers();
  // Forward safe headers
  for (const [key, value] of request.headers) {
    if (["cookie", "content-type", "accept", "accept-language"].includes(key.toLowerCase())) {
      headers.set(key, value);
    }
  }
  headers.set("host", new URL(BACKEND_URL).host);
  headers.set("x-forwarded-for", request.headers.get("x-forwarded-for") || "");
  headers.set("x-forwarded-proto", "https");

  const fetchOptions = {
    method: request.method,
    headers,
    redirect: "manual",
  };

  // Forward body for non-GET/HEAD requests
  if (request.method !== "GET" && request.method !== "HEAD") {
    fetchOptions.body = request.body;
    fetchOptions.duplex = "half";
  }

  const res = await fetch(target, fetchOptions);

  const responseHeaders = new Headers();
  for (const [key, value] of res.headers) {
    // Forward all headers except hop-by-hop ones
    if (!["transfer-encoding", "connection", "keep-alive"].includes(key.toLowerCase())) {
      responseHeaders.append(key, value);
    }
  }

  return new Response(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: responseHeaders,
  });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
