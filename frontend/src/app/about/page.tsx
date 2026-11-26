import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { ContentPageView, ContentSkeleton } from "@/components/content-page";
import { getPage } from "@/lib/api-server";

export async function generateMetadata(): Promise<Metadata> {
  await connection();
  let page: Awaited<ReturnType<typeof getPage>> | null = null;
  try {
    page = await getPage("about");
  } catch {
    page = null;
  }
  return {
    title: page?.seo_title || page?.title || "دربارهٔ ما",
    description: page?.seo_description || page?.summary || "آشنایی با فروشگاه فلاح و پسران.",
    alternates: { canonical: "/about" },
    robots: page?.requires_owner_review ? { index: false, follow: true } : undefined,
  };
}

async function About() {
  await connection();
  return <ContentPageView slug="about" />;
}

export default function AboutPage() {
  return (
    <Suspense fallback={<ContentSkeleton />}>
      <About />
    </Suspense>
  );
}
