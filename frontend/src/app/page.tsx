import Image, { getImageProps } from "next/image";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";

import { ProductGrid, ProductGridSkeleton } from "@/components/catalog";
import { FaqList } from "@/components/faq-list";
import { ChevronLeftIcon, PackageIcon, ScaleIcon, ShieldIcon, TruckIcon } from "@/components/icons";
import { getHome, getSite } from "@/lib/api-server";
import { absoluteUrl, jsonLd } from "@/lib/seo";
import type { Banner } from "@/lib/types";

const PROMISES = [
  {
    icon: ScaleIcon,
    title: "قیمت هر کیلو کنار هر بسته",
    text: "بسته‌های مختلف را با قیمت واحد مقایسه کنید.",
  },
  {
    icon: TruckIcon,
    title: "هزینهٔ ارسال پیش از پرداخت",
    text: "با انتخاب استان و شهر، هزینه و روش ارسال را می‌بینید.",
  },
  {
    icon: ShieldIcon,
    title: "پرداخت در درگاه بانکی",
    text: "اطلاعات کارت فقط در صفحهٔ بانک وارد می‌شود.",
  },
  {
    icon: PackageIcon,
    title: "پیگیری سفارش",
    text: "با شمارهٔ سفارش و شمارهٔ همراه، وضعیت سفارش را ببینید.",
  },
];

function HeroImage({ banner }: { banner: Banner }) {
  const common = { alt: banner.image_alt, fill: true, sizes: "100vw", quality: 80, fetchPriority: "high" as const, loading: "eager" as const };
  const { props: desktop } = getImageProps({ ...common, src: banner.image_desktop });
  if (!banner.image_mobile) {
    // eslint-disable-next-line @next/next/no-img-element -- props come from getImageProps (optimized srcset)
    return <img {...desktop} alt={banner.image_alt} className="-z-10 object-cover object-left" />;
  }
  const {
    props: { srcSet: mobileSrcSet },
  } = getImageProps({ ...common, src: banner.image_mobile });
  return (
    <picture>
      <source media="(max-width: 767px)" srcSet={mobileSrcSet} />
      <source media="(min-width: 768px)" srcSet={desktop.srcSet} />
      <img {...desktop} alt={banner.image_alt} className="-z-10 object-cover object-left" />
    </picture>
  );
}

function Hero({ banner }: { banner: Banner }) {
  return (
    <section className="relative isolate overflow-hidden bg-green-900">
      <HeroImage banner={banner} />
      <div className="absolute inset-0 -z-10 bg-gradient-to-l from-green-950/90 via-green-950/65 to-green-950/10 max-md:bg-gradient-to-t max-md:from-green-950/95 max-md:via-green-950/60 max-md:to-green-950/10" />
      <div className="container-page flex min-h-[30rem] flex-col justify-end py-12 sm:min-h-[34rem] md:justify-center lg:min-h-[38rem]">
        <div className="max-w-xl text-rice">
          {banner.eyebrow && <p className="text-sm font-semibold text-gold-200">{banner.eyebrow}</p>}
          <h1 className="mt-3 text-3xl font-extrabold leading-[1.45] sm:text-4xl lg:text-5xl lg:leading-[1.4]">
            {banner.title}
          </h1>
          {banner.subtitle && <p className="mt-4 text-base leading-8 text-cream/90 sm:text-lg">{banner.subtitle}</p>}
          <div className="mt-8 flex flex-wrap gap-3">
            {banner.cta_label && (
              <Link href={banner.cta_url || "/shop"} className="btn btn-gold min-w-36">
                {banner.cta_label}
              </Link>
            )}
            <Link
              href="/shop"
              className="btn border border-cream/50 text-rice hover:bg-rice/10"
            >
              همهٔ محصولات
            </Link>
          </div>
          {banner.is_generated_sample && (
            <p className="mt-6 text-xs text-cream/60">تصویر نمایشی است و محصول واقعی را نشان نمی‌دهد.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function HeroFallback() {
  return (
    <section className="bg-green-900">
      <div className="container-page flex min-h-[30rem] flex-col justify-end py-12 text-rice sm:min-h-[34rem] md:justify-center lg:min-h-[38rem]">
        <h1 className="max-w-xl text-3xl font-extrabold leading-[1.45] sm:text-4xl lg:text-5xl">
          برنج ایرانی برای سفرهٔ هر روز خانواده
        </h1>
        <div className="mt-8">
          <Link href="/shop" className="btn btn-gold">
            مشاهدهٔ محصولات
          </Link>
        </div>
      </div>
    </section>
  );
}

async function HomeContent() {
  await connection();
  const [home, site] = await Promise.all([getHome(), getSite()]);
  const banner = home.banners[0];
  const organization = {
    "@context": "https://schema.org",
    "@type": "Store",
    name: site.store.name,
    url: absoluteUrl("/"),
    logo: absoluteUrl("/brand/icon-512.png"),
    image: absoluteUrl("/brand/og-image.png"),
    email: site.store.email,
    telephone: `+98${site.store.phone.replace(/^0/, "")}`,
    address: { "@type": "PostalAddress", streetAddress: site.store.address, addressCountry: "IR" },
    sameAs: [`https://t.me/${site.store.telegram_username}`],
  };

  return (
    <>
      {banner ? <Hero banner={banner} /> : <HeroFallback />}

      <section aria-labelledby="promises" className="border-b border-line bg-cream/70">
        <h2 id="promises" className="sr-only">
          شیوهٔ خرید
        </h2>
        <ul className="container-page grid grid-cols-1 gap-x-6 gap-y-5 py-8 sm:grid-cols-2 lg:grid-cols-4">
          {PROMISES.map(({ icon: Icon, title, text }) => (
            <li key={title} className="flex items-start gap-3">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-white text-green-800 shadow-sm">
                <Icon />
              </span>
              <span>
                <span className="block font-bold text-ink">{title}</span>
                <span className="mt-1 block text-sm leading-6 text-ink-soft">{text}</span>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="categories-title" className="container-page pt-16">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-gold-700">دسته‌بندی‌ها</p>
            <h2 id="categories-title" className="mt-1 text-2xl font-extrabold text-green-800 sm:text-3xl">
              از برنج شروع کنید
            </h2>
          </div>
        </div>
        <ul className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {home.categories.map((category, index) => (
            <li key={category.slug} className={index === 0 ? "sm:col-span-2 lg:col-span-1 lg:row-span-1" : ""}>
              <Link
                href={`/category/${category.slug}`}
                className="group relative flex aspect-[4/3] overflow-hidden rounded-[var(--radius-card)] bg-green-900 shadow-[var(--shadow-card)] sm:aspect-[16/10] lg:aspect-[4/5]"
              >
                {category.image && (
                  <Image
                    src={category.image}
                    alt={category.image_alt}
                    fill
                    sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                    className="object-cover transition-transform duration-700 group-hover:scale-105"
                    quality={70}
                  />
                )}
                <span className="absolute inset-0 bg-gradient-to-t from-green-950/85 via-green-950/20 to-transparent" />
                <span className="relative mt-auto w-full p-5 text-rice sm:p-6">
                  <span className="flex items-center justify-between gap-3">
                    <span className="text-xl font-extrabold sm:text-2xl">{category.name}</span>
                    <span className="flex size-10 items-center justify-center rounded-full bg-rice/15 backdrop-blur transition-colors group-hover:bg-gold-500 group-hover:text-green-950">
                      <ChevronLeftIcon size={20} />
                    </span>
                  </span>
                  {category.description && (
                    <span className="mt-2 line-clamp-2 block text-sm leading-6 text-cream/85">
                      {category.description}
                    </span>
                  )}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      {home.featured.length > 0 && (
        <section aria-labelledby="featured-title" className="container-page pt-16">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-gold-700">محصولات</p>
              <h2 id="featured-title" className="mt-1 text-2xl font-extrabold text-green-800 sm:text-3xl">
                منتخب فروشگاه
              </h2>
            </div>
            <Link href="/shop" className="btn btn-ghost px-3 text-sm">
              همه
              <ChevronLeftIcon size={16} />
            </Link>
          </div>
          <div className="mt-8">
            <ProductGrid products={home.featured} />
          </div>
        </section>
      )}

      <section aria-labelledby="story-title" className="container-page pt-20">
        <div className="grid items-center gap-8 overflow-hidden rounded-[2rem] bg-cream lg:grid-cols-2">
          <div className="relative aspect-[4/3] lg:aspect-auto lg:h-full lg:min-h-[26rem]">
            <Image
              src="/brand/editorial-cooking.webp"
              alt="دیس برنج دم‌کشیده روی سفرهٔ خانگی"
              fill
              sizes="(min-width: 1024px) 50vw, 100vw"
              className="object-cover"
              quality={70}
            />
          </div>
          <div className="px-6 pb-10 sm:px-10 lg:py-12 lg:ps-0">
            <p className="text-sm font-semibold text-gold-700">راهنمای خرید برنج</p>
            <h2 id="story-title" className="mt-2 text-2xl font-extrabold leading-[1.6] text-green-800 sm:text-3xl">
              بستهٔ مناسب خانواده‌تان را انتخاب کنید
            </h2>
            <p className="mt-4 leading-8 text-ink-soft">
              برای هر بسته، وزن، قیمت بسته و قیمت هر کیلو را کنار هم نشان می‌دهیم تا مقایسه ساده باشد. اطلاعات رقم،
              منطقهٔ کشت و سال برداشت هر محصول در صفحهٔ همان محصول درج می‌شود.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/category/rice" className="btn btn-primary">
                مشاهدهٔ برنج‌ها
              </Link>
              <Link href="/faq" className="btn btn-secondary">
                پرسش‌های متداول
              </Link>
            </div>
          </div>
        </div>
      </section>

      {home.faqs.length > 0 && (
        <section aria-labelledby="faq-title" className="container-page pt-20">
          <div className="mx-auto max-w-3xl">
            <h2 id="faq-title" className="text-center text-2xl font-extrabold text-green-800 sm:text-3xl">
              پرسش‌های پرتکرار
            </h2>
            <div className="mt-8">
              <FaqList faqs={home.faqs.slice(0, 5)} />
            </div>
            <p className="mt-6 text-center">
              <Link href="/faq" className="font-semibold text-green-800 underline underline-offset-4">
                همهٔ پرسش‌ها
              </Link>
            </p>
          </div>
        </section>
      )}

      <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(organization)} />
    </>
  );
}

function HomeSkeleton() {
  return (
    <>
      <HeroFallback />
      <div className="container-page pt-16">
        <ProductGridSkeleton count={4} />
      </div>
    </>
  );
}

export default function HomePage() {
  return (
    <Suspense fallback={<HomeSkeleton />}>
      <HomeContent />
    </Suspense>
  );
}
