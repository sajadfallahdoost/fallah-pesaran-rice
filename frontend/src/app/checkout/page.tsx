import type { Metadata } from "next";

import { CheckoutForm } from "./checkout-form";

export const metadata: Metadata = {
  title: "تکمیل خرید",
  robots: { index: false, follow: false },
};

export default function CheckoutPage() {
  return (
    <div className="container-page py-8 sm:py-10">
      <h1 className="text-2xl font-extrabold text-green-800 sm:text-3xl">تکمیل خرید</h1>
      <CheckoutForm />
    </div>
  );
}
