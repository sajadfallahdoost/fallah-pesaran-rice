import type { Metadata } from "next";

import { PageIntro } from "@/components/catalog";

import { TrackForm } from "./track-form";

export const metadata: Metadata = {
  title: "پیگیری سفارش",
  description: "وضعیت سفارش خود را با شمارهٔ سفارش و شمارهٔ همراه ببینید.",
  alternates: { canonical: "/track" },
  robots: { index: false, follow: true },
};

export default function TrackPage() {
  return (
    <>
      <PageIntro
        title="پیگیری سفارش"
        description="شمارهٔ سفارش و شمارهٔ همراهی را که هنگام خرید وارد کردید بنویسید."
        crumbs={[{ label: "پیگیری سفارش" }]}
      />
      <div className="container-page max-w-3xl py-8">
        <TrackForm />
      </div>
    </>
  );
}
