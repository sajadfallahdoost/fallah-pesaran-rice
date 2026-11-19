import Link from "next/link";

import { EmptyState } from "@/components/catalog";

export default function NotFound() {
  return (
    <div className="container-page py-20">
      <EmptyState
        as="h1"
        title="صفحه‌ای که دنبالش بودید پیدا نشد"
        description="ممکن است نشانی اشتباه باشد یا این محصول دیگر عرضه نشود."
        action={
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/shop" className="btn btn-primary">
              مشاهدهٔ محصولات
            </Link>
            <Link href="/" className="btn btn-secondary">
              صفحهٔ اصلی
            </Link>
          </div>
        }
      />
    </div>
  );
}
