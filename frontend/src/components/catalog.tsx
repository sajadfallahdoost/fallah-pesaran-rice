import Image from "next/image";
import Link from "next/link";

import { ChevronLeftIcon } from "@/components/icons";
import { toman, tomanNumber } from "@/lib/format";
import { absoluteUrl, jsonLd } from "@/lib/seo";
import type { ProductCard as ProductCardData, UnitPrice } from "@/lib/types";

export function UnitPriceNote({ unit }: { unit: UnitPrice | null }) {
  if (!unit) return null;
  return (
    <span className="text-[0.8rem] text-ink-muted tabular">
      هر {unit.label} حدود {tomanNumber(unit.amount)} تومان
    </span>
  );
}

export function PriceTag({
  price,
  listPrice,
  size = "md",
}: {
  price: number;
  listPrice?: number;
  size?: "md" | "lg";
}) {
  const onSale = listPrice !== undefined && listPrice > price;
  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
      <span className={`font-bold text-green-800 tabular ${size === "lg" ? "text-2xl sm:text-[1.75rem]" : "text-lg"}`}>
        {tomanNumber(price)}
        <span className={`ms-1 font-medium text-ink-soft ${size === "lg" ? "text-base" : "text-sm"}`}>تومان</span>
      </span>
      {onSale && (
        <>
          <s className="text-sm text-ink-muted tabular" aria-label={`قیمت قبلی ${toman(listPrice)}`}>
            {tomanNumber(listPrice)}
          </s>
          <span className="rounded-full bg-gold-100 px-2 py-0.5 text-xs font-bold text-gold-700">
            {Math.round(((listPrice - price) / listPrice) * 100).toLocaleString("fa-IR")}٪ تخفیف
          </span>
        </>
      )}
    </span>
  );
}

export function SampleBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border border-gold-500/60 bg-gold-100 px-2.5 py-0.5 text-[0.72rem] font-semibold text-gold-700 ${className}`}
    >
      محصول نمونه
    </span>
  );
}

export function ProductCard({ product, priority = false }: { product: ProductCardData; priority?: boolean }) {
  const price = product.price_from;
  const href = `/product/${product.slug}`;
  return (
    <article className="group relative flex flex-col overflow-hidden rounded-[var(--radius-card)] border border-line bg-white shadow-[var(--shadow-card)] transition-shadow hover:shadow-[var(--shadow-lift)]">
      <div className="relative aspect-square overflow-hidden bg-cream">
        {product.image ? (
          <Image
            src={product.image.url}
            alt={product.image.alt}
            fill
            sizes="(min-width: 1280px) 300px, (min-width: 640px) 45vw, 92vw"
            className="object-cover transition-transform duration-500 group-hover:scale-[1.03]"
            loading={priority ? "eager" : "lazy"}
            quality={70}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-ink-muted">بدون تصویر</div>
        )}
        <div className="absolute inset-x-3 top-3 flex flex-wrap gap-1.5">
          {product.is_sample && <SampleBadge />}
          {!product.in_stock && (
            <span className="rounded-full bg-ink/80 px-2.5 py-0.5 text-[0.72rem] font-semibold text-rice">ناموجود</span>
          )}
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4 sm:p-5">
        <p className="text-xs font-medium text-gold-700">{product.category.name}</p>
        <h3 className="text-base font-bold leading-7 text-ink">
          <Link href={href} className="after:absolute after:inset-0 focus-visible:outline-none">
            {product.name}
          </Link>
        </h3>
        <p className="line-clamp-2 text-sm leading-6 text-ink-soft">{product.short_description}</p>
        <div className="mt-auto flex flex-col gap-1 pt-3">
          {price ? (
            <>
              <span className="text-xs text-ink-muted">
                {product.variant_count > 1 ? `از ${price.variant_title}` : price.variant_title}
              </span>
              <PriceTag price={price.price} listPrice={price.list_price} />
              <UnitPriceNote unit={price.unit_price} />
            </>
          ) : (
            <span className="text-sm text-ink-muted">قیمت به‌زودی</span>
          )}
        </div>
        <span className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-green-800" aria-hidden="true">
          {product.variant_count > 1 ? "انتخاب بسته" : "مشاهده و خرید"}
          <ChevronLeftIcon size={16} />
        </span>
      </div>
    </article>
  );
}

export function ProductGrid({ products }: { products: ProductCardData[] }) {
  const wide = products.length > 3 ? "xl:grid-cols-4" : "";
  return (
    <ul className={`grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 ${wide}`}>
      {products.map((product, index) => (
        <li key={product.id} className="flex">
          <div className="w-full">
            <ProductCard product={product} priority={index < 2} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ProductGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <li key={i} className="overflow-hidden rounded-[var(--radius-card)] border border-line bg-white">
          <div className="skeleton aspect-square rounded-none" />
          <div className="space-y-3 p-5">
            <div className="skeleton h-3 w-16" />
            <div className="skeleton h-5 w-3/4" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-6 w-1/2" />
          </div>
        </li>
      ))}
    </ul>
  );
}

export interface Crumb {
  href?: string;
  label: string;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  const all: Crumb[] = [{ href: "/", label: "خانه" }, ...items];
  const ld = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: all.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.label,
      ...(item.href ? { item: absoluteUrl(item.href) } : {}),
    })),
  };
  return (
    <nav aria-label="مسیر صفحه" className="text-sm text-ink-muted">
      <ol className="flex flex-wrap items-center gap-1.5">
        {all.map((item, index) => (
          <li key={`${item.label}-${index}`} className="flex items-center gap-1.5">
            {index > 0 && <ChevronLeftIcon size={14} className="text-ink-muted/60" />}
            {item.href && index < all.length - 1 ? (
              <Link href={item.href} className="inline-block py-0.5 hover:text-green-800 hover:underline">
                {item.label}
              </Link>
            ) : (
              <span aria-current="page" className="text-ink-soft">
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
      <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(ld)} />
    </nav>
  );
}

/** Owner-written text: blank line = paragraph, "## " = heading. Rendered as text, never HTML. */
export function RichText({ text, className = "" }: { text: string; className?: string }) {
  const blocks = text
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean);
  return (
    <div className={`prose-fa ${className}`}>
      {blocks.map((block, index) => {
        const lines = block.split("\n");
        if (lines[0].startsWith("## ")) {
          return (
            <div key={index}>
              <h2>{lines[0].slice(3)}</h2>
              {lines.length > 1 && <p>{lines.slice(1).join(" ")}</p>}
            </div>
          );
        }
        return <p key={index}>{lines.join(" ")}</p>;
      })}
    </div>
  );
}

export function PageIntro({
  title,
  description,
  crumbs,
  children,
}: {
  title: string;
  description?: string;
  crumbs: Crumb[];
  children?: React.ReactNode;
}) {
  return (
    <div className="border-b border-line bg-cream/60">
      <div className="container-page py-8 sm:py-10">
        <Breadcrumbs items={crumbs} />
        <h1 className="mt-4 text-2xl font-extrabold text-green-800 sm:text-3xl">{title}</h1>
        {description && <p className="mt-3 max-w-2xl leading-8 text-ink-soft">{description}</p>}
        {children}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  as: Heading = "h2",
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  as?: "h1" | "h2";
}) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center rounded-[var(--radius-card)] border border-dashed border-line bg-white/60 px-6 py-12 text-center">
      <Image src="/brand/fallah-emblem.svg" alt="" width={64} height={55} className="opacity-80" />
      <Heading className="mt-5 text-lg font-bold text-green-800">{title}</Heading>
      {description && <p className="mt-2 leading-7 text-ink-soft">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
