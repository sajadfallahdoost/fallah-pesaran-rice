"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useCart } from "@/components/cart-context";
import { api } from "@/lib/api-client";
import { faDigits, jalaliDate, toman } from "@/lib/format";
import type { AccountOrderSummary } from "@/lib/types";

import { AddressBook } from "./address-book";
import { LoginForm } from "./login-form";

type Me = { authenticated: boolean; phone?: string };

function safeNext(value: string | null): string | null {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : null;
}

export function AccountView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = safeNext(searchParams.get("next"));
  const { refresh: refreshCart } = useCart();
  const [me, setMe] = useState<Me | null>(null);
  const [orders, setOrders] = useState<AccountOrderSummary[] | null>(null);
  const [tab, setTab] = useState<"orders" | "addresses">("orders");

  const load = useCallback(async () => {
    const current = await api<Me>("/auth/me/").catch(() => ({ authenticated: false }));
    setMe(current);
    if (current.authenticated) {
      setOrders(await api<AccountOrderSummary[]>("/account/orders/").catch(() => []));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- session state lives on the server
    void load();
  }, [load]);

  async function onLoggedIn() {
    await refreshCart();
    if (next) {
      router.push(next);
      return;
    }
    await load();
  }

  async function logout() {
    await api("/auth/logout/", { method: "POST" }).catch(() => undefined);
    setOrders(null);
    setMe({ authenticated: false });
    await refreshCart();
  }

  if (!me) return <div className="skeleton mt-8 h-64" aria-busy="true" />;

  if (!me.authenticated) {
    return (
      <div className="mt-8 grid gap-8 md:grid-cols-[1fr_1fr]">
        <LoginForm onSuccess={onLoggedIn} />
        <div className="rounded-[var(--radius-card)] bg-cream/70 p-6 text-sm leading-8 text-ink-soft">
          <h2 className="text-base font-bold text-green-800">چرا وارد شوم؟</h2>
          <ul className="mt-2 list-disc ps-5">
            <li>دیدن همهٔ سفارش‌ها و وضعیت آن‌ها در یک جا</li>
            <li>ذخیرهٔ نشانی برای خریدهای بعدی</li>
          </ul>
          <p className="mt-3">ورود اختیاری است و بدون آن هم می‌توانید خرید کنید.</p>
          <p className="mt-3">
            سفارش قبلی دارید؟{" "}
            <Link href="/track" className="font-semibold text-green-800 underline underline-offset-4">
              پیگیری با شمارهٔ سفارش
            </Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-ink-soft">
          وارد شده با <span dir="ltr" className="font-semibold text-ink">{faDigits(me.phone ?? "")}</span>
        </p>
        <button type="button" onClick={logout} className="btn btn-ghost text-sm">
          خروج
        </button>
      </div>
      <div className="mt-6 flex gap-2 border-b border-line" role="tablist" aria-label="بخش‌های حساب">
        {(
          [
            ["orders", "سفارش‌ها"],
            ["addresses", "نشانی‌ها"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            id={`tab-${key}`}
            aria-selected={tab === key}
            aria-controls={`panel-${key}`}
            onClick={() => setTab(key)}
            className={`-mb-px min-h-11 border-b-2 px-4 font-semibold ${
              tab === key ? "border-green-800 text-green-800" : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="pt-6">
        {tab === "orders" ? (
          orders === null ? (
            <div className="skeleton h-40" />
          ) : orders.length === 0 ? (
            <div className="rounded-[var(--radius-card)] border border-dashed border-line p-8 text-center text-ink-soft">
              هنوز سفارشی با این حساب ثبت نشده است.{" "}
              <Link href="/shop" className="font-semibold text-green-800 underline">
                مشاهدهٔ محصولات
              </Link>
            </div>
          ) : (
            <ul className="flex flex-col gap-3">
              {orders.map((order) => (
                <li key={order.number}>
                  <Link
                    href={`/account/orders/${encodeURIComponent(order.number)}`}
                    className="card flex flex-wrap items-center justify-between gap-3 p-4 hover:border-green-700/50 sm:p-5"
                  >
                    <span>
                      <span dir="ltr" className="block font-mono font-bold text-ink">
                        {order.number}
                      </span>
                      <span className="text-sm text-ink-muted">{jalaliDate(order.created_at)}</span>
                    </span>
                    <span className="text-end">
                      <span className="block font-bold tabular text-green-800">{toman(order.grand_total)}</span>
                      <span className="text-sm text-ink-soft">
                        {order.status_label}
                        {order.status_label !== order.fulfillment_status_label && ` · ${order.fulfillment_status_label}`}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )
        ) : (
          <AddressBook />
        )}
      </div>
    </div>
  );
}
