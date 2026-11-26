import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageIntro, ProductGridSkeleton } from "@/components/catalog";
import { ListingFilters, ProductListing, readListingParams } from "@/components/product-listing";
import { getCategory, NotFoundError } from "@/lib/api-server";
import { listingRobots } from "@/lib/seo";

async function loadCategory(slug: string) {
  try {
    return await getCategory(slug);
  } catch (error) {
    if (error instanceof NotFoundError) notFound();
    throw error;
  }
}

export async function generateMetadata({
  params,
  searchParams,
}: PageProps<"/category/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const listing = readListingParams(await searchParams);
  const category = await getCategory(slug).catch(() => null);
  if (!category) return { title: "دسته‌بندی" };
  return {
    title: category.seo_title || `خرید ${category.name}`,
    description: category.seo_description || category.description,
    alternates: { canonical: `/category/${category.slug}` },
    openGraph: category.image ? { images: [{ url: category.image, alt: category.image_alt }] } : undefined,
    robots: listingRobots(listing),
  };
}

async function CategoryContent({ params, searchParams }: PageProps<"/category/[slug]">) {
  const { slug } = await params;
  const category = await loadCategory(slug);
  const listing = readListingParams(await searchParams);
  const basePath = `/category/${category.slug}`;
  return (
    <>
      <PageIntro
        title={category.name}
        description={category.description}
        crumbs={[{ href: "/shop", label: "محصولات" }, { label: category.name }]}
      />
      <div className="container-page py-8">
        <div className="card p-4 sm:p-5">
          <ListingFilters basePath={basePath} params={listing} />
        </div>
        <div className="mt-8">
          <ProductListing basePath={basePath} params={listing} category={category.slug} />
        </div>
      </div>
    </>
  );
}

export default function CategoryPage(props: PageProps<"/category/[slug]">) {
  return (
    <Suspense
      fallback={
        <div className="container-page py-10">
          <div className="skeleton mb-8 h-10 w-48" />
          <ProductGridSkeleton count={4} />
        </div>
      }
    >
      <CategoryContent {...props} />
    </Suspense>
  );
}
