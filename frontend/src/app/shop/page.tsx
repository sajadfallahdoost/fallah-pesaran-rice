import type { Metadata } from "next";
import { Suspense } from "react";

import { PageIntro, ProductGridSkeleton } from "@/components/catalog";
import { ListingFilters, ProductListing, readListingParams } from "@/components/product-listing";

export const metadata: Metadata = {
  title: "همهٔ محصولات",
  description: "خرید آنلاین برنج ایرانی، چای و روغن زیتون با نمایش قیمت هر کیلو و هزینهٔ ارسال پیش از پرداخت.",
  alternates: { canonical: "/shop" },
};

async function Listing({ searchParams }: { searchParams: PageProps<"/shop">["searchParams"] }) {
  const params = readListingParams(await searchParams);
  return (
    <>
      <div className="card p-4 sm:p-5">
        <ListingFilters basePath="/shop" params={params} />
      </div>
      <div className="mt-8">
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
