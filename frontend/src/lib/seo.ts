import type { StoreInfo } from "@/lib/types";

export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3010").replace(/\/$/, "");
export const HOME_TITLE = "برنج فلاح و پسران | برنج ایرانی، چای و روغن زیتون";
export const HOME_DESCRIPTION =
  "وب‌سایت فلاح و پسران در تهران، میرداماد. دسته‌های برنج ایرانی، چای و روغن زیتون، راهنماهای انتخاب و راه‌های تماس با فروشگاه را ببینید.";
export const INSTAGRAM_HANDLE = "fallah_rice.ir";
export const INSTAGRAM_URL = `https://www.instagram.com/${INSTAGRAM_HANDLE}/`;

export function absoluteUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

/** Serialize JSON-LD safely inside a <script> tag. */
export function jsonLd(data: unknown): { __html: string } {
  return { __html: JSON.stringify(data).replace(/</g, "\\u003c") };
}

export function organizationJsonLd(store: StoreInfo) {
  return {
    "@context": "https://schema.org",
    "@type": "Store",
    "@id": absoluteUrl("/#store"),
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
    sameAs: [INSTAGRAM_URL],
  };
}

export function websiteJsonLd(store: StoreInfo) {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": absoluteUrl("/#website"),
    name: store.name,
    url: absoluteUrl("/"),
    inLanguage: "fa-IR",
    publisher: { "@id": absoluteUrl("/#store") },
  };
}
