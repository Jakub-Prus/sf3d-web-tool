import { DEFAULT_BACKEND_PROXY_URL } from "@/lib/config";

type RouteContext = {
  params: Promise<{
    backendPath: string[];
  }>;
};

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

async function proxyToBackend(request: Request, context: RouteContext): Promise<Response> {
  const { backendPath } = await context.params;
  const incomingUrl = new URL(request.url);
  const backendBaseUrl = DEFAULT_BACKEND_PROXY_URL.replace(/\/$/, "");
  const backendUrl = new URL(`${backendBaseUrl}/${backendPath.join("/")}`);
  backendUrl.search = incomingUrl.search;

  const requestHeaders = new Headers(request.headers);
  for (const headerName of HOP_BY_HOP_HEADERS) {
    requestHeaders.delete(headerName);
  }

  const proxiedResponse = await fetch(backendUrl, {
    method: request.method,
    headers: requestHeaders,
    body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
    redirect: "manual",
  });

  const responseHeaders = new Headers(proxiedResponse.headers);
  for (const headerName of HOP_BY_HOP_HEADERS) {
    responseHeaders.delete(headerName);
  }

  return new Response(proxiedResponse.body, {
    status: proxiedResponse.status,
    statusText: proxiedResponse.statusText,
    headers: responseHeaders,
  });
}

export async function GET(request: Request, context: RouteContext) {
  return proxyToBackend(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return proxyToBackend(request, context);
}

export async function PUT(request: Request, context: RouteContext) {
  return proxyToBackend(request, context);
}

export async function PATCH(request: Request, context: RouteContext) {
  return proxyToBackend(request, context);
}

export async function DELETE(request: Request, context: RouteContext) {
  return proxyToBackend(request, context);
}

export async function OPTIONS(request: Request, context: RouteContext) {
  return proxyToBackend(request, context);
}
