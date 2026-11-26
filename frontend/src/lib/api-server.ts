import "server-only";

import { cacheLife, cacheTag } from "next/cache";

import type {
  Category,
  ContentPage,
  Faq,
  HomeData,
  Paginated,
  ProductCard,
  ProductDetail,
  SiteData,
} from "./types";

const BACKEND = process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8010";

export class NotFoundError extends Error {}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BACKEND}/api/v1${path}`, {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(8000),
  });
  if (response.status === 404) throw new NotFoundError(path);
  if (!response.ok) throw new Error(`Backend ${response.status} for ${path}`);
  return (await response.json()) as T;
}

// Catalog and content are owner-edited; Django posts to /api/revalidate with these tags on change.
// The short revalidate window also picks up stock changes caused by orders.

export async function getSite(): Promise<SiteData> {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  cacheTag("site");
  return getJson<SiteData>("/site/");
}

export async function getHome(): Promise<HomeData> {
  "use cache";
  cacheLife({ stale: 60, revalidate: 120, expire: 3600 });
  cacheTag("catalog", "content");
  return getJson<HomeData>("/home/");
}

export async function getCategories(): Promise<Category[]> {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  cacheTag("catalog");
  return getJson<Category[]>("/categories/");
}

export async function getCategory(slug: string): Promise<Category> {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  cacheTag("catalog");
  return getJson<Category>(`/categories/${encodeURIComponent(slug)}/`);
}

export interface ProductQuery {
  category?: string;
  q?: string;
  sort?: string;
  in_stock?: string;
  page?: string;
  page_size?: string;
}

export async function getProducts(query: ProductQuery): Promise<Paginated<ProductCard>> {
  "use cache";
  cacheLife({ stale: 30, revalidate: 60, expire: 3600 });
  cacheTag("catalog");
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) if (value) params.set(key, value);
  return getJson<Paginated<ProductCard>>(`/products/?${params.toString()}`);
}

export async function getProduct(slug: string): Promise<ProductDetail> {
  "use cache";
  cacheLife({ stale: 30, revalidate: 60, expire: 3600 });
  cacheTag("catalog", `product:${slug}`);
  return getJson<ProductDetail>(`/products/${encodeURIComponent(slug)}/`);
}

export async function getPage(slug: string): Promise<ContentPage> {
  "use cache";
  cacheLife({ stale: 300, revalidate: 3600, expire: 86400 });
  cacheTag("content");
  return getJson<ContentPage>(`/pages/${encodeURIComponent(slug)}/`);
}

export async function getFaqs(): Promise<Faq[]> {
  "use cache";
  cacheLife({ stale: 300, revalidate: 3600, expire: 86400 });
  cacheTag("content");
  return getJson<Faq[]>("/faqs/");
}
