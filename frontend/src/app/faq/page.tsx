import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { PageIntro } from "@/components/catalog";
import { FaqList } from "@/components/faq-list";
import { getFaqs } from "@/lib/api-server";
import { jsonLd } from "@/lib/seo";
import type { Faq } from "@/lib/types";

export const metadata: Metadata = {
  title: "پرسش‌های متداول",
  description: "پاسخ پرسش‌های رایج دربارهٔ خرید، ارسال، پرداخت و پیگیری سفارش در فلاح و پسران.",
  alternates: { canonical: "/faq" },
};

async function Faqs() {
  await connection();
  const faqs = await getFaqs().catch(() => [] as Faq[]);
  const groups = new Map<string, Faq[]>();
  for (const faq of faqs) groups.set(faq.group || "عمومی", [...(groups.get(faq.group || "عمومی") ?? []), faq]);
  const ld = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: { "@type": "Answer", text: faq.answer },
    })),
  };
  if (faqs.length === 0) return <p className="text-ink-soft">پرسشی ثبت نشده است.</p>;
  return (
    <div className="flex flex-col gap-10">
      {[...groups.entries()].map(([group, items]) => (
        <section key={group} aria-labelledby={`faq-${group}`}>
          <h2 id={`faq-${group}`} className="mb-4 text-lg font-bold text-green-800">
            {group}
          </h2>
          <FaqList faqs={items} />
        </section>
      ))}
      <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(ld)} />
    </div>
  );
}

export default function FaqPage() {
  return (
    <>
      <PageIntro title="پرسش‌های متداول" crumbs={[{ label: "پرسش‌های متداول" }]} />
      <div className="container-page max-w-3xl py-10">
        <Suspense fallback={<div className="skeleton h-64" />}>
          <Faqs />
        </Suspense>
      </div>
    </>
  );
}
