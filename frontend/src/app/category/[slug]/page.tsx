import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageIntro, ProductGridSkeleton } from "@/components/catalog";
import { ListingFilters, ProductListing, listingMetadata, readListingParams } from "@/components/product-listing";
import { listGuides } from "@/content/guides";
import { getCategory, getSite, hasLivePayment } from "@/lib/api-server";

const RICE_TITLE = "برنج ایرانی";

const categoryIntroductions: Record<string, string> = {
  rice: "برای خرید برنج ایرانی، وزن بسته، قیمت هر کیلو و موجودی را در فهرست ببینید. اگر برنج را برای وعده‌های روزمره یا مهمانی می‌خواهید، راهنماهای پایین صفحه به مقایسهٔ نتیجهٔ پخت و هزینه کمک می‌کنند.",
  tea: "چای عرضه‌شده و وزن بسته را در فهرست ببینید. برای انتخاب، مقدار مصرف و عطر و غلظتی را که در دم‌کرده ترجیح می‌دهید در نظر بگیرید.",
  "olive-oil": "برای انتخاب روغن زیتون، نوع درج‌شده روی برچسب و مقدار بسته را بررسی کنید. راهنماهای این صفحه دربارهٔ خواندن برچسب و انتخاب روغن برای سالاد یا آشپزی توضیح می‌دهند.",
};

async function loadCategory(slug: string) {
  const category = await getCategory(slug);
  if (!category) notFound();
  return category;
}

export async function generateMetadata({
  params,
  searchParams,
}: PageProps<"/category/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const listing = readListingParams(await searchParams);
  const [category, site] = await Promise.all([loadCategory(slug), getSite()]);
  const salesEnabled = site.store.sales_enabled;
  const name = category.slug === "rice" ? RICE_TITLE : category.name;
  const pageMetadata = await listingMetadata(`/category/${category.slug}`, listing, category.slug);
  return {
    ...pageMetadata,
    title: category.seo_title || (salesEnabled ? `خرید ${name}` : name),
    description: category.seo_description || (salesEnabled
      ? (categoryIntroductions[category.slug] || category.description || `بسته‌ها، قیمت و موجودی ${name} در فروشگاه فلاح و پسران.`)
      : `دستهٔ ${name} فلاح و پسران. نمونه‌ها، راهنماهای انتخاب و مسیر پرسش از فروشگاه را ببینید.`),
    openGraph: category.image ? { images: [{ url: category.image, alt: category.image_alt }] } : undefined,
    robots: category.product_count === 0 ? { index: false, follow: true } : pageMetadata.robots,
  };
}

async function CategoryContent({ params, searchParams }: PageProps<"/category/[slug]">) {
  const { slug } = await params;
  const [category, site, livePayment] = await Promise.all([loadCategory(slug), getSite(), hasLivePayment()]);
  const listing = readListingParams(await searchParams);
  const basePath = `/category/${category.slug}`;
  const name = category.slug === "rice" ? RICE_TITLE : category.name;
  const canOrderOnline = site.store.sales_enabled && livePayment;
  const guides = listGuides().filter((guide) => guide.relatedPaths.some((link) => link.href === basePath));
  return (
    <>
      <PageIntro
        title={name}
        description={categoryIntroductions[category.slug] || category.description || undefined}
        crumbs={[{ href: "/shop", label: "محصولات" }, { label: category.name }]}
      />
      <div className="container-page py-8">
        {!canOrderOnline && (
          <p className="mb-6 rounded-xl border border-line bg-cream p-4 text-sm leading-7 text-ink-soft">
            برای استعلام سفارش و پرسش دربارهٔ {name} از{" "}
            <Link href="/contact" className="font-semibold text-green-800 underline underline-offset-4">
              راه‌های تماس فلاح و پسران
            </Link>{" "}
            استفاده کنید.
          </p>
        )}
        <div className="card p-4 sm:p-5">
          <ListingFilters basePath={basePath} params={listing} />
        </div>
        <div className="mt-8">
          <h2 className="sr-only">فهرست محصولات {name}</h2>
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
