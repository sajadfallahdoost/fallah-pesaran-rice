import type { Metadata } from "next";
import { Suspense } from "react";

import { AccountView } from "./account-view";

export const metadata: Metadata = {
  title: "حساب کاربری",
  robots: { index: false, follow: false },
};

export default function AccountPage() {
  return (
    <div className="container-page max-w-4xl py-8 sm:py-10">
      <h1 className="text-2xl font-extrabold text-green-800 sm:text-3xl">حساب کاربری</h1>
      <Suspense fallback={<div className="skeleton mt-8 h-64" />}>
        <AccountView />
      </Suspense>
    </div>
  );
}
