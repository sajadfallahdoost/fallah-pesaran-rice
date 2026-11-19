import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { ContentPageView, ContentSkeleton } from "@/components/content-page";

export const metadata: Metadata = {
  title: "دربارهٔ ما",
  description: "آشنایی با فروشگاه فلاح و پسران.",
  alternates: { canonical: "/about" },
};

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
