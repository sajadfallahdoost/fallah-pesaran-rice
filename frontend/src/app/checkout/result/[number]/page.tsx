import type { Metadata } from "next";
import { Suspense } from "react";

import { PaymentResult } from "./payment-result";

export const metadata: Metadata = {
  title: "نتیجهٔ پرداخت",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

async function Result({ params }: { params: PageProps<"/checkout/result/[number]">["params"] }) {
  const { number } = await params;
  return <PaymentResult number={decodeURIComponent(number)} />;
}

export default function PaymentResultPage({ params }: PageProps<"/checkout/result/[number]">) {
  return (
    <div className="container-page max-w-3xl py-10">
      <Suspense fallback={<div className="skeleton h-80" aria-busy="true" />}>
        <Result params={params} />
      </Suspense>
    </div>
  );
}
