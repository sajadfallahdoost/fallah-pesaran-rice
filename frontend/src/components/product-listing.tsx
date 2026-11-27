import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { EmptyState, ProductGrid } from "@/components/catalog";
import { SearchIcon } from "@/components/icons";
import { getProducts } from "@/lib/api-server";
import { faDigits } from "@/lib/format";

export const SORT_OPTIONS = [
  { value: "featured", label: "پیشنهاد فروشگاه" },
  { value: "newest", label: "جدیدترین" },
  { value: "price_asc", label: "ارزان‌ترین" },
  { value: "price_desc", label: "گران‌ترین" },
];

export type ListingParams = { q?: string; sort?: string; in_stock?: string; page?: string };

export function readListingParams(raw: Record<string, string | string[] | undefined>): ListingParams {
  const pick = (key: string) => {
    const value = raw[key];
    return (Array.isArray(value) ? value[0] : value)?.slice(0, 80) || undefined;
  };
  const sort = pick("sort");
  const page = pick("page");
  const pageNumber = page && /^\d{1,4}$/.test(page) ? Number(page) : 1;
  return {
    q: pick("q"),
    sort: SORT_OPTIONS.some((o) => o.value === sort) ? sort : undefined,
    in_stock: pick("in_stock") === "1" ? "1" : undefined,
    page: pageNumber > 1 ? String(pageNumber) : undefined,
  };
}

export async function listingMetadata(
  path: string,
  params: ListingParams,
  category?: string,
): Promise<Pick<Metadata, "alternates" | "robots">> {
  if (params.page && !(await getProducts({ ...params, category }))) notFound();
  const hasFilter = Boolean(params.q || params.in_stock || (params.sort && params.sort !== "featured"));
  if (hasFilter) {
    return { alternates: { canonical: path }, robots: { index: false, follow: true } };
  }
  return { alternates: { canonical: params.page ? `${path}?page=${params.page}` : path } };
}

function hrefWith(basePath: string, params: ListingParams, change: Partial<ListingParams>): string {
  const merged: ListingParams = { ...params, page: undefined, ...change };
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(merged)) if (value) search.set(key, value);
  const query = search.toString();
  return query ? `${basePath}?${query}` : basePath;
}

export function ListingFilters({ basePath, params }: { basePath: string; params: ListingParams }) {
  return (
    <form action={basePath} method="get" role="search" className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div className="flex-1">
        <label htmlFor="q" className="field-label">
          جست‌وجو
        </label>
        <div className="relative">
          <SearchIcon size={18} className="pointer-events-none absolute inset-y-0 start-3 my-auto text-ink-muted" />
          <input
            id="q"
            name="q"
            type="search"
            defaultValue={params.q}
            placeholder="مثلاً برنج، چای…"
            className="field-input ps-10"
            maxLength={80}
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:flex sm:items-end">
        <div>
          <label htmlFor="sort" className="field-label">
            مرتب‌سازی
          </label>
          <select id="sort" name="sort" defaultValue={params.sort ?? "featured"} className="field-input sm:w-44">
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <label className="flex min-h-[2.875rem] cursor-pointer items-center gap-2 self-end rounded-xl border-[1.5px] border-line bg-white px-3 text-sm">
          <input
            type="checkbox"
            name="in_stock"
            value="1"
            defaultChecked={params.in_stock === "1"}
            className="size-4 accent-green-800"
          />
          فقط موجود
        </label>
      </div>
      <button type="submit" className="btn btn-primary">
        اعمال
      </button>
    </form>
  );
}

export async function ProductListing({
  basePath,
  params,
  category,
}: {
  basePath: string;
  params: ListingParams;
  category?: string;
}) {
  const data = await getProducts({ ...params, category }).catch(() => undefined);
  if (data === null) notFound();
  if (data === undefined) {
    return (
      <EmptyState
        title="فهرست محصولات بارگذاری نشد"
        description="ارتباط با فروشگاه برقرار نشد. چند لحظهٔ دیگر صفحه را دوباره باز کنید."
      />
    );
  }
  if (data.results.length === 0) {
    const filtered = Boolean(params.q || params.in_stock);
    return (
      <EmptyState
        title={filtered ? "محصولی با این شرایط پیدا نشد" : "به‌زودی محصولات این بخش اضافه می‌شود"}
        description={filtered ? "عبارت دیگری را جست‌وجو کنید یا فیلترها را بردارید." : undefined}
        action={
          filtered ? (
            <Link href={basePath} className="btn btn-secondary">
              حذف فیلترها
            </Link>
          ) : (
            <Link href="/shop" className="btn btn-secondary">
              همهٔ محصولات
            </Link>
          )
        }
      />
    );
  }
  const page = data.page;
  return (
    <div>
      <p className="mb-5 text-sm text-ink-muted" aria-live="polite">
        {faDigits(data.count)} محصول
        {params.q ? ` برای «${params.q}»` : ""}
      </p>
      <ProductGrid products={data.results} />
      {data.page_count > 1 && (
        <nav aria-label="صفحه‌بندی" className="mt-10 flex items-center justify-center gap-2">
          {Array.from({ length: data.page_count }, (_, i) => i + 1).map((n) => (
            <Link
              key={n}
              href={hrefWith(basePath, params, { page: n === 1 ? undefined : String(n) })}
              aria-current={n === page ? "page" : undefined}
              className={`flex size-11 items-center justify-center rounded-xl border text-sm font-semibold ${
                n === page ? "border-green-800 bg-green-800 text-rice" : "border-line bg-white hover:border-green-700"
              }`}
            >
              {faDigits(n)}
            </Link>
          ))}
        </nav>
      )}
    </div>
  );
}
