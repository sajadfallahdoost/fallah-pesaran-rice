"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { useCart } from "@/components/cart-context";
import { EmptyState, SampleBadge } from "@/components/catalog";
import { AlertIcon, InfoIcon, TrashIcon } from "@/components/icons";
import { QuantityStepper } from "@/components/quantity-stepper";
import { api, ApiError } from "@/lib/api-client";
import { faDigits, toman } from "@/lib/format";
import type { Cart, CartLine } from "@/lib/types";

export function CartSummary({ cart, children }: { cart: Cart; children?: React.ReactNode }) {
  return (
    <div className="card p-5 sm:p-6">
      <h2 className="text-lg font-bold text-green-800">خلاصهٔ سبد</h2>
      <dl className="mt-4 space-y-3 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-ink-soft">مبلغ کالاها ({faDigits(cart.item_count)} عدد)</dt>
          <dd className="tabular">{toman(cart.merchandise_total)}</dd>
        </div>
        {cart.discount_total > 0 && (
          <div className="flex justify-between gap-3 text-success">
            <dt>تخفیف</dt>
            <dd className="tabular">−{toman(cart.discount_total)}</dd>
          </div>
        )}
        <div className="flex justify-between gap-3 border-t border-line pt-3 text-base font-bold">
          <dt>جمع سبد</dt>
          <dd className="tabular text-green-800">{toman(cart.subtotal)}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs leading-6 text-ink-muted">هزینهٔ ارسال پس از وارد کردن استان و شهر محاسبه می‌شود.</p>
      {children}
    </div>
  );
}

function LineRow({ line, onChange }: { line: CartLine; onChange: (cart: Cart) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function update(quantity: number) {
    setBusy(true);
    setError("");
    try {
      const cart =
        quantity <= 0
          ? await api<Cart>(`/cart/items/${line.variant_id}/`, { method: "DELETE" })
          : await api<Cart>(`/cart/items/${line.variant_id}/`, { method: "PATCH", body: { quantity } });
      onChange(cart);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "به‌روزرسانی سبد انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="flex gap-4 py-5" aria-busy={busy}>
      <Link
        href={`/product/${line.product_slug}`}
        className="relative size-20 shrink-0 overflow-hidden rounded-xl bg-cream sm:size-24"
        tabIndex={-1}
        aria-hidden="true"
      >
        {line.image && <Image src={line.image.url} alt="" fill sizes="96px" className="object-cover" quality={70} />}
      </Link>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
          <div className="min-w-0">
            <Link href={`/product/${line.product_slug}`} className="font-bold text-ink hover:text-green-800">
              {line.product_name}
            </Link>
            <p className="text-sm text-ink-soft">{line.variant_title}</p>
            {line.is_sample && <SampleBadge className="mt-1" />}
          </div>
          <div className="text-end">
            <p className="font-bold text-green-800 tabular">{toman(line.line_total)}</p>
            {line.quantity > 1 && (
              <p className="text-xs text-ink-muted tabular">هر عدد {toman(line.unit_price)}</p>
            )}
          </div>
        </div>
        {line.price_changed_from !== null && !line.issue && (
          <p className="flex items-start gap-1.5 text-xs leading-6 text-gold-700">
            <InfoIcon size={16} className="mt-0.5 shrink-0" />
            قیمت این کالا از {toman(line.price_changed_from)} به {toman(line.unit_price)} تغییر کرده است.
          </p>
        )}
        {line.issue && (
          <p className="flex items-start gap-1.5 text-sm leading-6 text-danger" role="alert">
            <AlertIcon size={16} className="mt-1 shrink-0" />
            {line.issue}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3">
          {line.max_quantity > 0 && (
            <QuantityStepper
              value={Math.min(line.quantity, Math.max(line.max_quantity, 1))}
              max={line.max_quantity}
              onChange={update}
              disabled={busy}
              label={`تعداد ${line.product_name}`}
            />
          )}
          <button
            type="button"
            onClick={() => update(0)}
            disabled={busy}
            className="btn btn-ghost min-h-11 px-3 text-sm text-ink-soft hover:text-danger"
          >
            <TrashIcon size={18} />
            حذف
          </button>
        </div>
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
      </div>
    </li>
  );
}

export function CartView() {
  const { cart, loading, setCart } = useCart();

  if (loading && !cart) {
    return (
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_22rem]" aria-busy="true">
        <div className="space-y-4">
          <div className="skeleton h-28" />
          <div className="skeleton h-28" />
        </div>
        <div className="skeleton h-56" />
      </div>
    );
  }

  if (!cart || cart.lines.length === 0) {
    return (
      <div className="mt-10">
        <EmptyState
          title="سبد خرید شما خالی است"
          description="محصولات را ببینید و بستهٔ مناسب خود را به سبد اضافه کنید."
          action={
            <Link href="/shop" className="btn btn-primary">
              مشاهدهٔ محصولات
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="mt-8 grid items-start gap-8 lg:grid-cols-[1fr_22rem]">
      <section aria-label="کالاهای سبد" className="card px-5 sm:px-6">
        <ul className="divide-y divide-line">
          {cart.lines.map((line) => (
            <LineRow key={line.variant_id} line={line} onChange={setCart} />
          ))}
        </ul>
      </section>
      <div className="lg:sticky lg:top-24">
        <CartSummary cart={cart}>
          {cart.has_issues && (
            <p className="mt-4 rounded-xl bg-danger-soft px-4 py-3 text-sm leading-6 text-danger" role="alert">
              برای ادامه، کالاهایی را که پیام خطا دارند اصلاح یا حذف کنید.
            </p>
          )}
          {cart.has_issues ? (
            <button type="button" className="btn btn-primary mt-5 w-full" disabled>
              ادامهٔ خرید
            </button>
          ) : (
            <Link href="/checkout" className="btn btn-primary mt-5 w-full">
              ادامهٔ خرید
            </Link>
          )}
          <Link href="/shop" className="btn btn-ghost mt-2 w-full text-sm">
            افزودن کالای دیگر
          </Link>
        </CartSummary>
      </div>
    </div>
  );
}
