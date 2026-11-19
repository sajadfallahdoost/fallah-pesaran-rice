"use client";

import Link from "next/link";
import { useState } from "react";

import { useCart } from "@/components/cart-context";
import { PriceTag, UnitPriceNote } from "@/components/catalog";
import { AlertIcon, CartIcon, CheckIcon } from "@/components/icons";
import { QuantityStepper } from "@/components/quantity-stepper";
import { api, ApiError } from "@/lib/api-client";
import { faDigits, jalaliDate, toman } from "@/lib/format";
import type { Cart, Variant } from "@/lib/types";

function stockText(variant: Variant): { text: string; tone: "ok" | "low" | "out" } {
  switch (variant.stock_status) {
    case "in_stock":
      return { text: "موجود", tone: "ok" };
    case "low_stock":
      return {
        text: variant.low_stock_count ? `فقط ${faDigits(variant.low_stock_count)} عدد باقی مانده` : "موجودی محدود",
        tone: "low",
      };
    default:
      return { text: "ناموجود", tone: "out" };
  }
}

export function BuyBox({
  productName,
  variants,
  purchasable,
  salesEnabled,
}: {
  productName: string;
  variants: Variant[];
  purchasable: boolean;
  salesEnabled: boolean;
}) {
  const firstAvailable = variants.find((v) => v.stock_status === "in_stock" || v.stock_status === "low_stock");
  const [selectedId, setSelectedId] = useState<number | undefined>((firstAvailable ?? variants[0])?.id);
  const [quantity, setQuantity] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [added, setAdded] = useState(false);
  const { setCart, announce } = useCart();

  const variant = variants.find((v) => v.id === selectedId);
  if (!variant) return <p className="text-ink-muted">این محصول فعلاً بستهٔ قابل فروش ندارد.</p>;

  const stock = stockText(variant);
  const canBuy = purchasable && salesEnabled && stock.tone !== "out" && variant.max_quantity > 0;

  async function addToCart() {
    if (!variant) return;
    setBusy(true);
    setError("");
    setAdded(false);
    try {
      const cart = await api<Cart>("/cart/items/", {
        method: "POST",
        body: { variant_id: variant.id, quantity },
      });
      setCart(cart);
      setAdded(true);
      announce(`${productName}، ${variant.title} به سبد اضافه شد.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "افزودن به سبد انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {variants.length > 1 && (
        <fieldset>
          <legend className="field-label">انتخاب بسته</legend>
          <div className="grid grid-cols-1 gap-2.5 xs:grid-cols-2">
            {variants.map((v) => {
              const out = v.stock_status === "out_of_stock" || v.stock_status === "unavailable";
              const checked = v.id === selectedId;
              return (
                <label
                  key={v.id}
                  className={`relative flex cursor-pointer flex-col gap-0.5 rounded-xl border-[1.5px] px-4 py-3 transition-colors ${
                    checked ? "border-green-800 bg-green-50" : "border-line bg-white hover:border-green-700/50"
                  } ${out ? "opacity-70" : ""}`}
                >
                  <input
                    type="radio"
                    name="variant"
                    value={v.id}
                    checked={checked}
                    onChange={() => {
                      setSelectedId(v.id);
                      setQuantity(1);
                      setAdded(false);
                      setError("");
                    }}
                    className="sr-only"
                  />
                  <span className="flex items-center justify-between gap-2 font-bold text-ink">
                    {v.title}
                    {checked && <CheckIcon size={18} className="text-green-800" />}
                  </span>
                  <span className="text-sm text-ink-soft tabular">
                    {out ? "ناموجود" : toman(v.price)}
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>
      )}

      <div className="rounded-[var(--radius-card)] bg-cream/70 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-sm text-ink-soft">{variant.title}</span>
          <span
            className={`inline-flex items-center gap-1.5 text-sm font-semibold ${
              stock.tone === "ok" ? "text-success" : stock.tone === "low" ? "text-gold-700" : "text-danger"
            }`}
          >
            <span
              className={`size-2 rounded-full ${
                stock.tone === "ok" ? "bg-success" : stock.tone === "low" ? "bg-gold-500" : "bg-danger"
              }`}
              aria-hidden="true"
            />
            {stock.text}
          </span>
        </div>
        <div className="mt-3">
          <PriceTag price={variant.price} listPrice={variant.list_price} size="lg" />
        </div>
        <div className="mt-1.5">
          <UnitPriceNote unit={variant.unit_price} />
        </div>
        {variant.on_sale && variant.sale_ends_at && (
          <p className="mt-2 text-xs text-gold-700">تخفیف تا {jalaliDate(variant.sale_ends_at)}</p>
        )}
      </div>

      {canBuy ? (
        <div className="flex flex-wrap items-center gap-3">
          <QuantityStepper
            value={quantity}
            max={variant.max_quantity}
            onChange={(next) => {
              setQuantity(Math.max(1, Math.min(variant.max_quantity, next)));
              setAdded(false);
            }}
            label="تعداد"
          />
          <button type="button" className="btn btn-primary flex-1" onClick={addToCart} disabled={busy} aria-busy={busy}>
            <CartIcon size={20} />
            {busy ? "در حال افزودن…" : "افزودن به سبد خرید"}
          </button>
        </div>
      ) : (
        <p className="rounded-xl border border-line bg-white px-4 py-3 text-sm text-ink-soft">
          {!salesEnabled
            ? "ثبت سفارش موقتاً غیرفعال است."
            : !purchasable
              ? "این محصول فعلاً برای فروش عرضه نمی‌شود."
              : "این بسته فعلاً موجود نیست. بستهٔ دیگری را انتخاب کنید یا بعداً سر بزنید."}
        </p>
      )}

      {error && (
        <p role="alert" className="flex items-start gap-2 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
          <AlertIcon size={18} className="mt-0.5 shrink-0" />
          {error}
        </p>
      )}
      {added && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-success-soft px-4 py-3 text-sm text-success">
          <span className="flex items-center gap-2">
            <CheckIcon size={18} />
            به سبد خرید اضافه شد.
          </span>
          <Link href="/cart" className="font-bold underline underline-offset-4">
            ادامهٔ خرید و پرداخت
          </Link>
        </div>
      )}
    </div>
  );
}
