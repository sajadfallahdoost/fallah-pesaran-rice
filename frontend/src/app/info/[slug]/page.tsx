import type { Metadata } from "next";
import { Suspense } from "react";

import { ContentPageView, ContentSkeleton } from "@/components/content-page";
import { getPage } from "@/lib/api-server";

export async function generateMetadata({ params }: PageProps<"/info/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage(slug).catch(() => null);
  if (!page) return { title: "صفحه" };
  return {
    title: page.seo_title || page.title,
    description: page.seo_description || page.summary,
    alternates: { canonical: `/info/${page.slug}` },
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
