import "server-only";

import { cacheLife, cacheTag } from "next/cache";

import type {
  Category,
  ContentPage,
  Faq,
  HomeData,
  Paginated,
  PaymentProviderInfo,
  ProductCard,
  ProductDetail,
  SiteData,
} from "./types";

const BACKEND = process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8010";

function getJson<T>(path: string): Promise<T>;
function getJson<T>(path: string, allowNotFound: true): Promise<T | null>;
async function getJson<T>(path: string, allowNotFound = false): Promise<T | null> {
  const response = await fetch(`${BACKEND}/api/v1${path}`, {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(8000),
  });
  if (allowNotFound && response.status === 404) return null;
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

export async function getCategory(slug: string): Promise<Category | null> {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  cacheTag("catalog");
  return getJson<Category>(`/categories/${encodeURIComponent(slug)}/`, true);
}

export interface ProductQuery {
  category?: string;
  q?: string;
  sort?: string;
  in_stock?: string;
  page?: string;
  page_size?: string;
}

export async function getProducts(query: ProductQuery): Promise<Paginated<ProductCard> | null> {
  "use cache";
  cacheLife({ stale: 30, revalidate: 60, expire: 3600 });
  cacheTag("catalog");
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) if (value) params.set(key, value);
  return getJson<Paginated<ProductCard>>(`/products/?${params.toString()}`, true);
}

export async function getProduct(slug: string): Promise<ProductDetail | null> {
  "use cache";
  cacheLife({ stale: 30, revalidate: 60, expire: 3600 });
  cacheTag("catalog", `product:${slug}`);
  return getJson<ProductDetail>(`/products/${encodeURIComponent(slug)}/`, true);
}

export async function getPage(slug: string): Promise<ContentPage | null> {
  "use cache";
  cacheLife({ stale: 300, revalidate: 3600, expire: 86400 });
  cacheTag("content");
  return getJson<ContentPage>(`/pages/${encodeURIComponent(slug)}/`, true);
}

async function getPaymentProviders(): Promise<PaymentProviderInfo[]> {
  "use cache";
  cacheLife({ stale: 30, revalidate: 60, expire: 3600 });
  return getJson<PaymentProviderInfo[]>("/payments/providers/");
}

export async function hasLivePayment(): Promise<boolean> {
  const providers = await getPaymentProviders().catch(() => []);
  return providers.some((provider) => !provider.is_test);
}

export async function getFaqs(): Promise<Faq[]> {
  "use cache";
  cacheLife({ stale: 300, revalidate: 3600, expire: 86400 });
  cacheTag("content");
  return getJson<Faq[]>("/faqs/");
}
