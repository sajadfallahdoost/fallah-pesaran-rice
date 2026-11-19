"use client";

import Link from "next/link";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="container-page py-20">
      <div className="mx-auto max-w-md rounded-[var(--radius-card)] border border-line bg-white px-6 py-12 text-center">
        <h1 className="text-lg font-bold text-green-800">مشکلی در نمایش این صفحه پیش آمد</h1>
        <p className="mt-2 leading-7 text-ink-soft">
          ممکن است ارتباط با فروشگاه موقتاً قطع شده باشد. چند لحظهٔ دیگر دوباره تلاش کنید.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={reset} className="btn btn-primary">
            تلاش دوباره
          </button>
          <Link href="/" className="btn btn-secondary">
            صفحهٔ اصلی
          </Link>
        </div>
      </div>
    </div>
  );
}
