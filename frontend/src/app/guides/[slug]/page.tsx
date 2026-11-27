import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Breadcrumbs, RichText } from "@/components/catalog";
import { getGuide, listGuides } from "@/content/guides";
import { jalaliDate } from "@/lib/format";
import { absoluteUrl, jsonLd } from "@/lib/seo";

export function generateStaticParams() {
  return listGuides().map((guide) => ({ slug: guide.slug }));
}

export async function generateMetadata({ params }: PageProps<"/guides/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const guide = getGuide(slug);
  if (!guide) notFound();
  return {
    title: guide.seoTitle,
    description: guide.seoDescription,
    alternates: { canonical: `/guides/${guide.slug}` },
    openGraph: {
      type: "article",
      title: guide.seoTitle,
      description: guide.seoDescription,
      ...(guide.publishedAt ? { publishedTime: guide.publishedAt } : {}),
      images: [{ url: guide.image.src, alt: guide.image.alt }],
      modifiedTime: guide.updatedAt,
    },
  };
}

export default async function GuidePage({ params }: PageProps<"/guides/[slug]">) {
  const { slug } = await params;
  const guide = getGuide(slug);
  if (!guide) notFound();

  const article = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: guide.title,
    description: guide.description,
    ...(guide.publishedAt ? { datePublished: guide.publishedAt } : {}),
    image: absoluteUrl(guide.image.src),
    dateModified: guide.updatedAt,
    inLanguage: "fa-IR",
    mainEntityOfPage: absoluteUrl(`/guides/${guide.slug}`),
    publisher: {
      "@type": "Organization",
      name: "فلاح و پسران",
      logo: { "@type": "ImageObject", url: absoluteUrl("/brand/icon-512.png") },
    },
  };

  return (
    <>
      <div className="border-b border-line bg-cream/60">
        <div className="container-page py-8 sm:py-10">
          <Breadcrumbs items={[{ href: "/guides", label: "مجلهٔ برنج فلاح" }, { label: guide.title }]} />
          <p className="mt-4 text-sm font-semibold text-gold-700">{guide.cluster}</p>
          <h1 className="mt-2 text-2xl font-extrabold text-green-800 sm:text-3xl">{guide.title}</h1>
          <p className="mt-3 max-w-2xl leading-8 text-ink-soft">{guide.description}</p>
        </div>
      </div>
      <article className="container-page max-w-3xl py-10">
        <div className="relative mb-8 aspect-video overflow-hidden rounded-[var(--radius-card)] bg-cream">
          <Image
            src={guide.image.src}
            alt={guide.image.alt}
            fill
            sizes="(min-width: 768px) 720px, 100vw"
            className="object-cover"
            quality={80}
          />
        </div>
        <RichText text={guide.body} />
        <nav aria-label="پیوندهای مرتبط" className="mt-12 rounded-[var(--radius-card)] bg-cream/70 p-6">
          <h2 className="text-lg font-bold text-green-800">مطالب و محصولات مرتبط</h2>
          <ul className="mt-4 space-y-2">
            {guide.relatedPaths.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="font-semibold text-green-800 underline underline-offset-4">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <p className="mt-8 text-xs text-ink-muted">آخرین به‌روزرسانی: {jalaliDate(guide.updatedAt)}</p>
      </article>
      <script type="application/ld+json" dangerouslySetInnerHTML={jsonLd(article)} />
    </>
  );
}
