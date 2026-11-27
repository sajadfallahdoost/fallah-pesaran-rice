import type { Metadata } from "next";
import { Suspense } from "react";

import { PageIntro, ProductGridSkeleton } from "@/components/catalog";
import { ListingFilters, ProductListing, listingMetadata, readListingParams } from "@/components/product-listing";

export async function generateMetadata({ searchParams }: PageProps<"/shop">): Promise<Metadata> {
  const params = readListingParams(await searchParams);
  return {
    title: "همهٔ محصولات",
    description: "فهرست محصولات فلاح و پسران در دسته‌های برنج ایرانی، چای و روغن زیتون.",
    ...await listingMetadata("/shop", params),
  };
}

async function Listing({ searchParams }: { searchParams: PageProps<"/shop">["searchParams"] }) {
  const params = readListingParams(await searchParams);
  return (
    <>
      <div className="card p-4 sm:p-5">
        <ListingFilters basePath="/shop" params={params} />
      </div>
      <div className="mt-8">
        <h2 className="sr-only">فهرست محصولات</h2>
        <ProductListing basePath="/shop" params={params} />
      </div>
    </>
  );
}

export default function ShopPage({ searchParams }: PageProps<"/shop">) {
  return (
    <>
      <PageIntro title="همهٔ محصولات" crumbs={[{ label: "همهٔ محصولات" }]} />
      <div className="container-page py-8">
        <Suspense fallback={<ProductGridSkeleton count={4} />}>
          <Listing searchParams={searchParams} />
        </Suspense>
      </div>
    </>
  );
}
