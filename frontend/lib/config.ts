const SAME_ORIGIN_API_BASE_URL = "/api";
const DIRECT_BACKEND_FALLBACK_URL = "http://127.0.0.1:8000/api";

export const DEFAULT_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? SAME_ORIGIN_API_BASE_URL;

export const DEFAULT_BACKEND_PROXY_URL =
  process.env.BACKEND_PROXY_URL ?? DIRECT_BACKEND_FALLBACK_URL;

export const ACCEPTED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];

export function resolveApiUrl(pathOrUrl: string): string {
  if (/^https?:\/\//i.test(pathOrUrl)) {
    return pathOrUrl;
  }
  if (pathOrUrl.startsWith("/")) {
    return pathOrUrl;
  }
  return new URL(pathOrUrl, `${DEFAULT_API_BASE_URL}/`).toString();
}
