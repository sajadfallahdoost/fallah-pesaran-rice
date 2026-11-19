import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { BuyBox } from "@/components/buy-box";
import { Breadcrumbs, ProductGrid, RichText, SampleBadge } from "@/components/catalog";
import { InfoIcon, ShieldIcon, TruckIcon } from "@/components/icons";
import { ProductGallery } from "@/components/product-gallery";
import { getProduct, getSite, NotFoundError } from "@/lib/api-server";
import { absoluteUrl, jsonLd } from "@/lib/seo";
import type { ProductDetail } from "@/lib/types";

async function loadProduct(slug: string) {
  try {
    return await getProduct(slug);
  } catch (error) {
    if (error instanceof NotFoundError) notFound();
    throw error;
  }
}

export async function generateMetadata({ params }: PageProps<"/product/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProduct(slug).catch(() => null);
  if (!product) return { title: "محصول" };
  const image = product.images[0] ?? product.image;
  return {
    title: product.seo_title || product.name,
    description: product.seo_description || product.short_description,
    alternates: { canonical: `/product/${product.slug}` },
    openGraph: image ? { images: [{ url: image.url, alt: image.alt }] } : undefined,
    robots: product.is_sample ? { index: false, follow: true } : undefined,
  };
}

function productJsonLd(product: ProductDetail) {
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    sku: product.sku,
    description: product.short_description,
    image: product.images.map((image) => absoluteUrl(image.url)),
    brand: { "@type": "Brand", name: "فلاح و پسران" },
    category: product.category.name,
    offers: product.variants.map((variant) => ({
      "@type": "Offer",
      sku: variant.sku,
      name: variant.title,
      price: variant.price,
      priceCurrency: "IRR",
      availability:
        variant.stock_status === "in_stock" || variant.stock_status === "low_stock"
          ? "https://schema.org/InStock"
          : "https://schema.org/OutOfStock",
      url: absoluteUrl(`/product/${product.slug}`),
    })),
  };
}

async function ProductContent({ params }: { params: PageProps<"/product/[slug]">["params"] }) {
  const { slug } = await params;
  const [product, site] = await Promise.all([loadProduct(slug), getSite().catch(() => null)]);
  const salesEnabled = site?.store.sales_enabled ?? true;

  return (
    <>
      <div className="container-page pt-6">
        <Breadcrumbs
          items={[
            { href: `/category/${product.category.slug}`, label: product.category.name },
            { label: product.name },
          ]}
        />
      </div>

      <div className="container-page grid gap-8 pt-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-12">
        <div className="lg:sticky lg:top-24 lg:self-start">
          <ProductGallery images={product.images} name={product.name} />
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href={`/category/${product.category.slug}`}
              className="text-sm font-semibold text-gold-700 hover:underline"
            >
              {product.category.name}
            </Link>
            {product.is_sample && <SampleBadge />}
          </div>
          <h1 className="mt-2 text-2xl font-extrabold leading-[1.6] text-green-800 sm:text-3xl">{product.name}</h1>
          <p className="mt-3 leading-8 text-ink-soft">{product.short_description}</p>

          {product.is_sample && (
            <p className="mt-4 flex items-start gap-2 rounded-xl border border-gold-500/40 bg-gold-100/60 px-4 py-3 text-sm leading-7 text-gold-700">
              <InfoIcon size={18} className="mt-1 shrink-0" />
              این محصول نمونهٔ نمایشی است؛ قیمت، موجودی و تصویر آن آزمایشی است و پیش از فروش واقعی باید توسط مالک
              فروشگاه تأیید شود.
            </p>
          )}

          <div className="mt-6">
            <BuyBox
              productName={product.name}
              variants={product.variants}
              purchasable={product.purchasable}
              salesEnabled={salesEnabled}
            />
          </div>

          <ul className="mt-6 grid gap-3 text-sm text-ink-soft sm:grid-cols-2">
            <li className="flex items-start gap-2.5 rounded-xl border border-line bg-white px-4 py-3">
              <TruckIcon size={20} className="mt-0.5 shrink-0 text-green-800" />
              هزینهٔ ارسال بر اساس استان، شهر و وزن، پیش از پرداخت نمایش داده می‌شود.
            </li>
            <li className="flex items-start gap-2.5 rounded-xl border border-line bg-white px-4 py-3">
              <ShieldIcon size={20} className="mt-0.5 shrink-0 text-green-800" />
              پرداخت فقط در صفحهٔ درگاه بانکی؛ اطلاعات کارت در این سایت وارد نمی‌شود.
            </li>
          </ul>

          {product.attributes.length > 0 && (
            <section aria-labelledby="specs" className="mt-10">
              <h2 id="specs" className="text-lg font-bold text-green-800">
                مشخصات
              </h2>
              <dl className="mt-4 divide-y divide-line overflow-hidden rounded-[var(--radius-card)] border border-line bg-white">
                {product.attributes.map((attribute) => (
                  <div key={attribute.name} className="grid grid-cols-[8rem_1fr] gap-4 px-5 py-3 text-sm sm:grid-cols-[10rem_1fr]">
                    <dt className="text-ink-muted">{attribute.name}</dt>
                    <dd className="text-ink">{attribute.value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          {product.description && (
            <section aria-labelledby="about-product" className="mt-10">
              <h2 id="about-product" className="text-lg font-bold text-green-800">
                دربارهٔ محصول
              </h2>
              <RichText text={product.description} className="mt-3" />
            </section>
          )}

          {product.storage_and_use && (
            <section aria-label="نگهداری و مصرف" className="mt-6 rounded-[var(--radius-card)] bg-cream/70 p-5 sm:p-6">
              <RichText text={product.storage_and_use} className="[&_h2:first-child]:mt-0" />
            </section>
          )}
        </div>
      </div>

      {product.related.length > 0 && (
        <section aria-labelledby="related" className="container-page pt-16">
          <h2 id="related" className="text-2xl font-extrabold text-green-800">
            محصولات دیگر
          </h2>
          <div className="mt-6">
            <ProductGrid products={product.related} />
          </div>
        </section>
      )}

      <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(productJsonLd(product))} />
    </>
  );
}

function ProductSkeleton() {
  return (
    <div className="container-page grid gap-8 py-10 lg:grid-cols-2" aria-hidden="true">
      <div className="skeleton aspect-square" />
      <div className="space-y-4">
        <div className="skeleton h-4 w-20" />
        <div className="skeleton h-9 w-3/4" />
        <div className="skeleton h-5 w-full" />
        <div className="skeleton h-28 w-full" />
        <div className="skeleton h-12 w-full" />
      </div>
    </div>
  );
}

export default function ProductPage({ params }: PageProps<"/product/[slug]">) {
  return (
    <Suspense fallback={<ProductSkeleton />}>
      <ProductContent params={params} />
    </Suspense>
  );
}
