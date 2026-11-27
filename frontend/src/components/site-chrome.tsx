import Image from "next/image";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";

import { CartButton, MobileMenu, NavLink } from "@/components/header-client";
import { InfoIcon, MailIcon, MenuIcon, PhoneIcon, PinIcon, SearchIcon, TelegramIcon, UserIcon } from "@/components/icons";
import { getSite } from "@/lib/api-server";
import { PHONE_DISPLAY, PHONE_HREF } from "@/lib/format";
import type { SiteData } from "@/lib/types";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="flex shrink-0 items-center gap-2.5" aria-label="فلاح و پسران، صفحهٔ اصلی">
      <Image src="/brand/fallah-emblem.svg" alt="" width={44} height={38} loading="eager" className="h-9 w-auto sm:h-10" />
      {!compact && (
        <span className="flex flex-col leading-tight">
          <span className="text-lg font-extrabold text-green-800 sm:text-xl">فلاح و پسران</span>
          <span className="hidden text-[0.72rem] text-ink-muted sm:block">برنج ایرانی و خوراکی‌های برگزیده</span>
        </span>
      )}
    </Link>
  );
}

const STATIC_LINKS = [
  { href: "/shop", label: "همهٔ محصولات" },
  { href: "/guides", label: "مجله" },
  { href: "/about", label: "دربارهٔ ما" },
  { href: "/contact", label: "تماس" },
];

function navItems(site: SiteData | null) {
  const categories = (site?.navigation ?? []).map((c) => ({ href: `/category/${c.slug}`, label: c.name }));
  return [STATIC_LINKS[0], ...categories, ...STATIC_LINKS.slice(1)];
}

function MenuButtonPlaceholder() {
  return (
    <span className="inline-flex size-11 shrink-0 items-center justify-center text-green-800 lg:hidden" aria-hidden="true">
      <MenuIcon />
    </span>
  );
}

function HeaderFrame({ site }: { site: SiteData | null }) {
  const items = navItems(site);
  const phone = site?.store.phone ?? "09122122187";
  return (
    <header className="sticky top-0 z-40 border-b border-line/80 bg-rice/95 backdrop-blur supports-[backdrop-filter]:bg-rice/85">
      <div className="container-page flex h-16 items-center gap-2 sm:h-[4.5rem] lg:gap-6">
        <Suspense fallback={<MenuButtonPlaceholder />}>
          <MobileMenu
            items={[...items, { href: "/track", label: "پیگیری سفارش" }, { href: "/faq", label: "پرسش‌های متداول" }]}
            phone={phone}
          />
        </Suspense>
        <Logo />
        <nav aria-label="منوی اصلی" className="ms-4 hidden flex-1 items-center gap-1 lg:flex">
          {items.map((item) => (
            <Suspense
              key={item.href}
              fallback={
                <Link href={item.href} className="rounded-lg px-3 py-2 text-[0.95rem] text-ink-soft hover:text-green-800">
                  {item.label}
                </Link>
              }
            >
              <NavLink {...item} />
            </Suspense>
          ))}
        </nav>
        <div className="ms-auto flex items-center gap-0.5 lg:ms-0">
          <Link
            href="/shop"
            className="hidden size-11 items-center justify-center rounded-xl text-green-800 hover:bg-green-50 xs:inline-flex"
            aria-label="جست‌وجو در محصولات"
          >
            <SearchIcon />
          </Link>
          <Link
            href="/account"
            className="inline-flex size-11 items-center justify-center rounded-xl text-green-800 hover:bg-green-50"
            aria-label="حساب کاربری"
          >
            <UserIcon />
          </Link>
          <CartButton />
        </div>
      </div>
    </header>
  );
}

export function HeaderFallback() {
  return <HeaderFrame site={null} />;
}

export async function Header() {
  await connection();
  const site = await getSite().catch(() => null);
  return (
    <>
      {site?.demo_mode && (
        <div className="bg-green-900 text-rice">
          <p className="container-page flex items-center justify-center gap-2 py-2 text-center text-[0.8rem] leading-6">
            <InfoIcon size={16} className="shrink-0 text-gold-200" />
            موارد نمایشی فروشگاه با برچسب نمونه مشخص شده‌اند.
          </p>
        </div>
      )}
      {site?.store.announcement && (
        <div className="bg-gold-100 text-green-900">
          <p className="container-page py-2 text-center text-sm">{site.store.announcement}</p>
        </div>
      )}
      <HeaderFrame site={site} />
    </>
  );
}

export async function Footer() {
  await connection();
  const site = await getSite().catch(() => null);
  const store = site?.store;
  const year = new Intl.DateTimeFormat("fa-IR-u-ca-persian", { year: "numeric", timeZone: "Asia/Tehran" }).format(
    new Date(),
  );
  return (
    <footer className="mt-20 bg-green-900 text-cream">
      <div className="container-page grid gap-10 py-14 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1.2fr]">
        <div>
          <div className="flex items-center gap-3">
            <span className="rounded-xl bg-cream p-1.5">
              <Image src="/brand/fallah-emblem.svg" alt="" width={40} height={34} />
            </span>
            <span className="text-xl font-extrabold text-rice">{store?.name ?? "فلاح و پسران"}</span>
          </div>
          <p className="mt-4 max-w-xs text-sm leading-7 text-cream/80">
            {store?.tagline || "برنج ایرانی و خوراکی‌های برگزیده برای سفرهٔ خانواده"}
          </p>
          <p className="mt-4 max-w-xs text-xs leading-6 text-cream/65">
            پرداخت فقط در صفحهٔ درگاه بانکی انجام می‌شود. شمارهٔ کارت، رمز دوم یا CVV2 را هرگز در این سایت وارد نکنید.
          </p>
        </div>
        <nav aria-label="دسته‌بندی‌ها">
          <h2 className="text-sm font-bold text-gold-200">فروشگاه</h2>
          <ul className="mt-4 space-y-1.5 text-sm">
            <li>
              <Link className="inline-block py-1 hover:text-rice hover:underline" href="/shop">
                همهٔ محصولات
              </Link>
            </li>
            {(site?.navigation ?? []).map((c) => (
              <li key={c.slug}>
                <Link className="inline-block py-1 hover:text-rice hover:underline" href={`/category/${c.slug}`}>
                  {c.name}
                </Link>
              </li>
            ))}
            <li>
              <Link className="inline-block py-1 hover:text-rice hover:underline" href="/track">
                پیگیری سفارش
              </Link>
            </li>
          </ul>
        </nav>
        <nav aria-label="راهنما و قوانین">
          <h2 className="text-sm font-bold text-gold-200">راهنما</h2>
          <ul className="mt-4 space-y-1.5 text-sm">
            <li>
              <Link className="inline-block py-1 hover:text-rice hover:underline" href="/guides">
                راهنمای خرید
              </Link>
            </li>
            <li>
              <Link className="inline-block py-1 hover:text-rice hover:underline" href="/faq">
                پرسش‌های متداول
              </Link>
            </li>
            {(site?.pages ?? [])
              .filter((p) => p.slug !== "about")
              .map((p) => (
                <li key={p.slug}>
                  <Link className="inline-block py-1 hover:text-rice hover:underline" href={`/info/${p.slug}`}>
                    {p.title}
                  </Link>
                </li>
              ))}
            <li>
              <Link className="inline-block py-1 hover:text-rice hover:underline" href="/about">
                دربارهٔ ما
              </Link>
            </li>
            <li>
              <Link className="inline-block py-1 hover:text-rice hover:underline" href="/contact">
                تماس با ما
              </Link>
            </li>
          </ul>
        </nav>
        <div>
          <h2 className="text-sm font-bold text-gold-200">ارتباط با ما</h2>
          {store && (
            <ul className="mt-4 space-y-3 text-sm">
              <li className="flex items-start gap-2.5">
                <PinIcon size={18} className="mt-0.5 shrink-0 text-gold-200" />
                <span>{store.address}</span>
              </li>
              <li>
                <a href={PHONE_HREF(store.phone)} className="flex items-center gap-2.5 hover:text-rice hover:underline">
                  <PhoneIcon size={18} className="shrink-0 text-gold-200" />
                  <span dir="ltr">{PHONE_DISPLAY(store.phone)}</span>
                </a>
              </li>
              <li>
                <a href={`mailto:${store.email}`} className="flex items-center gap-2.5 hover:text-rice hover:underline">
                  <MailIcon size={18} className="shrink-0 text-gold-200" />
                  <span dir="ltr" className="break-all">
                    {store.email}
                  </span>
                </a>
              </li>
              <li>
                <a
                  href={`https://t.me/${store.telegram_username}`}
                  className="flex items-center gap-2.5 hover:text-rice hover:underline"
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  <TelegramIcon size={18} className="shrink-0 text-gold-200" />
                  <span dir="ltr">@{store.telegram_username}</span>
                </a>
              </li>
            </ul>
          )}
        </div>
      </div>
      <div className="border-t border-cream/10">
        <p className="container-page py-5 text-center text-xs text-cream/60">
          © {year} {store?.name ?? "فلاح و پسران"}
        </p>
      </div>
    </footer>
  );
}
