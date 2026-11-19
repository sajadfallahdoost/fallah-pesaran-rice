import type { Metadata } from "next";

import { CartView } from "./cart-view";

export const metadata: Metadata = {
  title: "سبد خرید",
  robots: { index: false, follow: false },
};

export default function CartPage() {
  return (
    <div className="container-page py-8 sm:py-10">
      <h1 className="text-2xl font-extrabold text-green-800 sm:text-3xl">سبد خرید</h1>
      <CartView />
    </div>
  );
}
