import type { Metadata } from "next";
import { Suspense } from "react";

import { ContentPageView, ContentSkeleton, loadPage } from "@/components/content-page";

export async function generateMetadata({ params }: PageProps<"/info/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const page = await loadPage(slug);
  return {
    title: page.seo_title || page.title,
    description: page.seo_description || page.summary,
    alternates: { canonical: `/info/${page.slug}` },
    robots: page.requires_owner_review ? { index: false, follow: true } : undefined,
  };
}

async function Content({ params }: { params: PageProps<"/info/[slug]">["params"] }) {
  const { slug } = await params;
  return <ContentPageView slug={slug} />;
}

export default function InfoPage({ params }: PageProps<"/info/[slug]">) {
  return (
    <Suspense fallback={<ContentSkeleton />}>
      <Content params={params} />
    </Suspense>
  );
}
