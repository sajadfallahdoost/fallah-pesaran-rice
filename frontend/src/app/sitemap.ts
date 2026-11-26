import type { MetadataRoute } from "next";
import { connection } from "next/server";

import { listGuides } from "@/content/guides";
import { getCategories, getProducts, getSite, type ProductQuery } from "@/lib/api-server";
import { SITE_URL } from "@/lib/seo";

async function allCatalogProducts() {
  const query: ProductQuery = { page: "1", page_size: "48" };
  const first = await getProducts(query);
  const pages = Math.max(1, first.page_count);
  if (pages === 1) return first.results;
  const rest = await Promise.all(
    Array.from({ length: pages - 1 }, (_, index) => getProducts({ ...query, page: String(index + 2) })),
  );
  return [...first.results, ...rest.flatMap((page) => page.results)];
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  await connection();
  const guides = listGuides().map((guide) => ({
    url: `${SITE_URL}/guides/${guide.slug}`,
    lastModified: new Date(guide.updatedAt),
  }));
  const fixed: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/` },
    { url: `${SITE_URL}/shop` },
    { url: `${SITE_URL}/contact` },
    { url: `${SITE_URL}/faq` },
    { url: `${SITE_URL}/guides` },
    ...guides,
  ];

  // A failed catalog request must surface as an error instead of a successful, incomplete sitemap.
  const [site, categories, products] = await Promise.all([getSite(), getCategories(), allCatalogProducts()]);
  return [
    ...fixed,
    ...categories.map((category) => ({
      url: `${SITE_URL}/category/${category.slug}`,
      lastModified: category.updated_at ? new Date(category.updated_at) : undefined,
    })),
    ...products
      .filter((product) => !product.is_sample)
      .map((product) => ({
        url: `${SITE_URL}/product/${product.slug}`,
        lastModified: product.updated_at ? new Date(product.updated_at) : undefined,
      })),
    ...site.pages
      .filter((page) => page.requires_owner_review === false)
      .map((page) => ({
        url: `${SITE_URL}${page.slug === "about" ? "/about" : `/info/${page.slug}`}`,
        lastModified: page.updated_at ? new Date(page.updated_at) : undefined,
      })),
  ];
}
