import type { Metadata } from "next";

import type { StoreInfo } from "@/lib/types";

export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3010").replace(/\/$/, "");

export function absoluteUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

/** Serialize JSON-LD safely inside a <script> tag. */
export function jsonLd(data: unknown): { __html: string } {
  return { __html: JSON.stringify(data).replace(/</g, "\\u003c") };
}

/** Filtered/sorted/paginated listings stay crawlable but should not compete with canonical URLs. */
export function listingRobots(params: {
  q?: string;
  sort?: string;
  in_stock?: string;
  page?: string;
}): Metadata["robots"] {
  const hasFilter = Boolean(params.q || params.in_stock || params.page || (params.sort && params.sort !== "featured"));
  return hasFilter ? { index: false, follow: true } : undefined;
}

export function organizationJsonLd(store: StoreInfo) {
  return {
    "@context": "https://schema.org",
    "@type": "Store",
    name: store.name,
    url: absoluteUrl("/"),
    logo: absoluteUrl("/brand/icon-512.png"),
    image: absoluteUrl("/brand/og-image.png"),
    email: store.email,
    telephone: `+98${store.phone.replace(/^0/, "")}`,
    address: {
      "@type": "PostalAddress",
      streetAddress: store.address,
      addressCountry: "IR",
    },
    sameAs: [`https://t.me/${store.telegram_username}`],
  };
}

export function websiteJsonLd(store: StoreInfo) {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: store.name,
    url: absoluteUrl("/"),
    inLanguage: "fa-IR",
    potentialAction: {
      "@type": "SearchAction",
      target: {
        "@type": "EntryPoint",
        urlTemplate: `${absoluteUrl("/shop")}?q={search_term_string}`,
      },
      "query-input": "required name=search_term_string",
    },
  };
}
