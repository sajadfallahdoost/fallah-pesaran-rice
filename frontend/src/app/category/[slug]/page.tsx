import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageIntro, ProductGridSkeleton } from "@/components/catalog";
import { ListingFilters, ProductListing, readListingParams } from "@/components/product-listing";
import { listGuides } from "@/content/guides";
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
    title: category.seo_title || (category.slug === "rice" ? "خرید برنج ایرانی" : `خرید ${category.name}`),
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
  const guides = listGuides().filter((guide) => guide.relatedPaths.some((link) => link.href === basePath));
  return (
    <>
      <PageIntro
        title={category.slug === "rice" ? "برنج ایرانی" : category.name}
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
        {guides.length > 0 && (
          <nav aria-labelledby="category-guides" className="card mt-10 p-5 sm:p-6">
            <h2 id="category-guides" className="text-lg font-bold text-green-800">
              {`راهنمای انتخاب ${category.name}`}
            </h2>
            <ul className="mt-4 grid gap-4 sm:grid-cols-2">
              {guides.map((guide) => (
                <li key={guide.slug}>
                  <Link href={`/guides/${guide.slug}`} className="font-semibold text-green-800 underline underline-offset-4">
                    {guide.title}
                  </Link>
                  <p className="mt-1 text-sm leading-7 text-ink-soft">{guide.description}</p>
                </li>
              ))}
            </ul>
          </nav>
        )}
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
