import { timingSafeEqual } from "node:crypto";

import { revalidateTag } from "next/cache";
import { type NextRequest, NextResponse } from "next/server";

const ALLOWED_TAGS = /^(site|catalog|content|product:[a-z0-9-]{1,120})$/;

function secretMatches(given: string | null): boolean {
  const expected = process.env.STOREFRONT_REVALIDATE_SECRET ?? "";
  if (expected.length < 16 || !given) return false;
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function POST(request: NextRequest) {
  if (!secretMatches(request.headers.get("x-revalidate-secret"))) {
    return NextResponse.json({ ok: false }, { status: 401 });
  }
  let tags: unknown;
  try {
    tags = ((await request.json()) as { tags?: unknown }).tags;
  } catch {
    return NextResponse.json({ ok: false }, { status: 400 });
  }
  if (!Array.isArray(tags) || tags.length === 0 || tags.length > 20) {
    return NextResponse.json({ ok: false }, { status: 400 });
  }
  const valid = tags.filter((tag): tag is string => typeof tag === "string" && ALLOWED_TAGS.test(tag));
  for (const tag of valid) revalidateTag(tag, { expire: 0 });
  return NextResponse.json({ ok: true, revalidated: valid });
}
