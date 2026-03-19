const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function apiFetch(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const headers = isFormData
    ? { ...options.headers }
    : { "Content-Type": "application/json", ...options.headers };

  // Strip trailing slash to avoid Next.js 308 redirect loops;
  // the server-side proxy always adds one for Django.
  const cleanPath = path.endsWith("/") ? path.slice(0, -1) : path;

  const res = await fetch(`${API_BASE}${cleanPath}`, {
    credentials: "include",
    headers,
    ...options,
  });
  return res;
}
