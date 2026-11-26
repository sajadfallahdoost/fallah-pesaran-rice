import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";

import { PageIntro } from "@/components/catalog";
import { MailIcon, PhoneIcon, PinIcon, TelegramIcon } from "@/components/icons";
import { getSite } from "@/lib/api-server";
import { PHONE_DISPLAY, PHONE_HREF } from "@/lib/format";
import { jsonLd, organizationJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: "تماس با ما",
  description: "راه‌های ارتباط با فروشگاه فلاح و پسران: تلفن، ایمیل و تلگرام.",
  alternates: { canonical: "/contact" },
};

async function ContactCards() {
  await connection();
  const site = await getSite().catch(() => null);
  if (!site) return <p className="text-ink-soft">اطلاعات تماس بارگذاری نشد. کمی بعد دوباره تلاش کنید.</p>;
  const { store } = site;
  const organization = organizationJsonLd(store);
  const cards = [
    {
      icon: PhoneIcon,
      title: "تلفن همراه",
      value: <span dir="ltr">{PHONE_DISPLAY(store.phone)}</span>,
      href: PHONE_HREF(store.phone),
      action: "تماس",
    },
    {
      icon: TelegramIcon,
      title: "تلگرام",
      value: <span dir="ltr">@{store.telegram_username}</span>,
      href: `https://t.me/${store.telegram_username}`,
      action: "ارسال پیام",
      external: true,
    },
    {
      icon: MailIcon,
      title: "ایمیل",
      value: (
        <span dir="ltr" className="break-all">
          {store.email}
        </span>
      ),
      href: `mailto:${store.email}`,
      action: "ارسال ایمیل",
    },
  ];
  return (
    <>
      <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map(({ icon: Icon, title, value, href, action, external }) => (
          <li key={title} className="card flex flex-col gap-3 p-6">
            <span className="flex size-12 items-center justify-center rounded-xl bg-green-50 text-green-800">
              <Icon />
            </span>
            <h2 className="font-bold text-ink">{title}</h2>
            <p className="text-lg font-semibold text-green-800">{value}</p>
            <a
              href={href}
              className="btn btn-secondary mt-auto"
              {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
            >
              {action}
            </a>
          </li>
        ))}
      </ul>
      <div className="card mt-5 flex items-start gap-4 p-6">
        <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-green-50 text-green-800">
          <PinIcon />
        </span>
        <div>
          <h2 className="font-bold text-ink">نشانی</h2>
          <p className="mt-1 text-lg text-ink-soft">{store.address}</p>
          {store.business_hours && <p className="mt-2 text-sm text-ink-muted">ساعت پاسخ‌گویی: {store.business_hours}</p>}
        </div>
      </div>
      <p className="mt-8 text-sm leading-7 text-ink-soft">
        برای پیگیری سفارش، شمارهٔ سفارش را همراه داشته باشید یا از صفحهٔ{" "}
        <Link href="/track" className="font-semibold text-green-800 underline">
          پیگیری سفارش
        </Link>{" "}
        استفاده کنید. برای راهنمای انتخاب محصول هم می‌توانید{" "}
        <Link href="/guides" className="font-semibold text-green-800 underline">
          راهنماهای خرید
        </Link>{" "}
        را بخوانید.
      </p>
      <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(organization)} />
    </>
  );
}

export default function ContactPage() {
  return (
    <>
      <PageIntro title="تماس با ما" crumbs={[{ label: "تماس با ما" }]} />
      <div className="container-page py-10">
        <Suspense fallback={<div className="skeleton h-56" />}>
          <ContactCards />
        </Suspense>
      </div>
    </>
  );
}
