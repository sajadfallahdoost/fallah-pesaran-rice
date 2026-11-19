import type { Metadata } from "next";
import { Suspense } from "react";

import { AccountOrder } from "./account-order";

export const metadata: Metadata = {
  title: "جزئیات سفارش",
  robots: { index: false, follow: false },
};

async function Content({ params }: { params: PageProps<"/account/orders/[number]">["params"] }) {
  const { number } = await params;
  return <AccountOrder number={decodeURIComponent(number)} />;
}

export default function AccountOrderPage({ params }: PageProps<"/account/orders/[number]">) {
  return (
    <div className="container-page max-w-3xl py-8 sm:py-10">
      <Suspense fallback={<div className="skeleton h-80" />}>
        <Content params={params} />
      </Suspense>
    </div>
  );
}
