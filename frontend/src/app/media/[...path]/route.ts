import type { NextRequest } from "next/server";

// Next's image optimizer fetches local images through an internal request without a Host header,
// which Django rejects; this handler proxies uploaded media with a proper request instead of a rewrite.
// Django serves uploads only in development; in production nginx serves the media volume.
const MEDIA_ORIGIN = (
  process.env.MEDIA_INTERNAL_URL ?? `${process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8010"}/media`
).replace(/\/$/, "");
const SAFE_SEGMENT = /^[A-Za-z0-9._-]{1,200}$/;
const PASS_HEADERS = ["content-type", "content-length", "etag", "last-modified", "cache-control"];

export async function GET(request: NextRequest, { params }: RouteContext<"/media/[...path]">) {
  const { path } = await params;
  if (path.length === 0 || path.length > 6 || !path.every((s) => SAFE_SEGMENT.test(s) && !/^\.+$/.test(s))) {
    return new Response("Not found", { status: 404 });
  }
  const conditional: Record<string, string> = {};
  for (const name of ["if-none-match", "if-modified-since"]) {
    const value = request.headers.get(name);
    if (value) conditional[name] = value;
  }
  let upstream: Response;
  try {
    upstream = await fetch(`${MEDIA_ORIGIN}/${path.map(encodeURIComponent).join("/")}`, {
      headers: conditional,
      signal: AbortSignal.timeout(10_000),
      cache: "no-store",
    });
  } catch {
    return new Response("Upstream unavailable", { status: 502 });
  }
  if (upstream.status === 304) return new Response(null, { status: 304 });
  const type = upstream.headers.get("content-type") ?? "";
  if (!upstream.ok || !/^image\/(webp|avif|jpeg|png|gif)$/.test(type)) return new Response("Not found", { status: 404 });
  const headers = new Headers();
  for (const name of PASS_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (!headers.has("cache-control")) headers.set("cache-control", "public, max-age=86400");
  headers.set("x-content-type-options", "nosniff");
  return new Response(upstream.body, { status: 200, headers });
}
