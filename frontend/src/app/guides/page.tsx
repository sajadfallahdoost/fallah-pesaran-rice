import type { Metadata } from "next";
import Link from "next/link";

import { PageIntro } from "@/components/catalog";
import { ChevronLeftIcon } from "@/components/icons";
import { listGuides } from "@/content/guides";
import { absoluteUrl, jsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: "مجلهٔ برنج فلاح",
  description:
    "راهنماهای خرید برنج ایرانی، تشخیص کیفیت، تفاوت ارقام، پخت و نگهداری، چای و روغن زیتون در فروشگاه فلاح و پسران.",
  alternates: { canonical: "/guides" },
};

export default function GuidesIndexPage() {
  const guides = listGuides();
  const itemList = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    itemListElement: guides.map((guide, index) => ({
      "@type": "ListItem",
      position: index + 1,
      url: absoluteUrl(`/guides/${guide.slug}`),
      name: guide.title,
    })),
  };

  return (
    <>
      <PageIntro
        title="مجلهٔ برنج فلاح"
        description="راهنمای خرید، پخت و نگهداری برنج ایرانی و انتخاب چای و روغن زیتون."
        crumbs={[{ label: "راهنماها" }]}
      />
      <div className="container-page py-10">
        <ul className="grid gap-5 sm:grid-cols-2">
          {guides.map((guide) => (
            <li key={guide.slug}>
              <Link
                href={`/guides/${guide.slug}`}
                className="group flex h-full flex-col rounded-[var(--radius-card)] border border-line bg-white p-6 shadow-[var(--shadow-card)] transition-shadow hover:shadow-[var(--shadow-lift)]"
              >
                <p className="text-sm font-semibold text-gold-700">{guide.cluster}</p>
                <h2 className="mt-2 text-xl font-extrabold text-green-800 group-hover:underline">{guide.title}</h2>
                <p className="mt-3 flex-1 leading-8 text-ink-soft">{guide.description}</p>
                <span className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-green-800">
                  ادامه
                  <ChevronLeftIcon size={16} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(itemList)} />
    </>
  );
}
