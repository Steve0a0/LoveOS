const BACKEND_URL = process.env.BACKEND_URL;

async function handler(request, { params }) {
  const { path } = await params;
  const targetPath = path.join("/");
  const url = new URL(request.url);
  // Always add trailing slash — Django expects it on every endpoint
  const target = `${BACKEND_URL}/api/${targetPath}/${url.search}`;

  const headers = new Headers();
  // Forward all request headers except host
  for (const [key, value] of request.headers) {
    const lower = key.toLowerCase();
    if (lower === "host" || lower === "transfer-encoding") continue;
    headers.set(key, value);
  }
  headers.set("host", new URL(BACKEND_URL).host);

  const fetchOptions = {
    method: request.method,
    headers,
  };

  // Forward body for non-GET/HEAD requests
  if (request.method !== "GET" && request.method !== "HEAD") {
    fetchOptions.body = request.body;
    fetchOptions.duplex = "half";
  }

  const res = await fetch(target, fetchOptions);

  const responseHeaders = new Headers();
  for (const [key, value] of res.headers) {
    const lower = key.toLowerCase();
    // Skip hop-by-hop and encoding headers (Node fetch auto-decompresses)
    if (
      lower === "transfer-encoding" ||
      lower === "connection" ||
      lower === "keep-alive" ||
      lower === "content-encoding" ||
      lower === "content-length"
    ) {
      continue;
    }
    responseHeaders.append(key, value);
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
