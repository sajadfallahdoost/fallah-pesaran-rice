import type { MetadataRoute } from "next";
import { connection } from "next/server";

import { getCategories, getProducts, getSite } from "@/lib/api-server";
import { SITE_URL } from "@/lib/seo";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  await connection();
  const fixed = ["", "/shop", "/about", "/contact", "/faq", "/track"].map((path) => ({ url: `${SITE_URL}${path}` }));
  try {
    const [site, categories, products] = await Promise.all([
      getSite(),
      getCategories(),
      getProducts({ page: undefined }),
    ]);
    return [
      ...fixed,
      ...categories.map((c) => ({ url: `${SITE_URL}/category/${c.slug}` })),
      ...products.results.filter((p) => !p.is_sample).map((p) => ({ url: `${SITE_URL}/product/${p.slug}` })),
      ...site.pages.filter((p) => p.slug !== "about").map((p) => ({ url: `${SITE_URL}/info/${p.slug}` })),
    ];
  } catch {
    return fixed;
  }
}
