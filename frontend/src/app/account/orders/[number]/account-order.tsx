"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ChevronLeftIcon } from "@/components/icons";
import {
  OrderItems,
  OrderProgress,
  OrderShipments,
  OrderTimeline,
  OrderTotals,
  StageBadge,
} from "@/components/order-view";
import { api, ApiError } from "@/lib/api-client";
import { faDigits, jalaliDateTime } from "@/lib/format";
import type { OrderPrivate } from "@/lib/types";

export function AccountOrder({ number }: { number: string }) {
  const [order, setOrder] = useState<OrderPrivate | null>(null);
  const [error, setError] = useState<{ message: string; auth: boolean } | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<OrderPrivate>(`/account/orders/${encodeURIComponent(number)}/`)
      .then((data) => !cancelled && setOrder(data))
      .catch((err) => {
        if (cancelled) return;
        setError({
          message: err instanceof ApiError ? err.message : "سفارش بارگذاری نشد.",
          auth: err instanceof ApiError && err.status === 401,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [number]);

  if (error) {
    return (
      <div className="rounded-[var(--radius-card)] bg-danger-soft px-5 py-6 text-danger" role="alert">
        <p>{error.auth ? "برای دیدن این سفارش وارد حساب شوید." : error.message}</p>
        <Link
          href={error.auth ? `/account?next=/account/orders/${encodeURIComponent(number)}` : "/account"}
          className="btn btn-secondary mt-4"
        >
          {error.auth ? "ورود" : "بازگشت به حساب"}
        </Link>
      </div>
    );
  }
  if (!order) return <div className="skeleton h-80" aria-busy="true" />;

  return (
    <div className="flex flex-col gap-6">
      <Link href="/account" className="inline-flex items-center gap-1 self-start text-sm font-semibold text-green-800">
        <ChevronLeftIcon size={16} className="rotate-180" />
        سفارش‌های من
      </Link>
      <section className="card p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-extrabold text-green-800">
            سفارش <span dir="ltr" className="font-mono">{order.number}</span>
          </h1>
          <StageBadge stage={order.stage} />
        </div>
        <p className="mt-1 text-sm text-ink-muted">ثبت: {jalaliDateTime(order.created_at)}</p>
        <div className="mt-6">
          <OrderProgress stage={order.stage} />
        </div>
        <div className="mt-6">
          <OrderShipments order={order} />
        </div>
        <div className="mt-4">
          <OrderItems order={order} />
        </div>
        <div className="mt-3 border-t border-line pt-4">
          <OrderTotals order={order} />
        </div>
        <div className="mt-5 rounded-xl bg-cream/70 px-4 py-3 text-sm leading-7 text-ink-soft">
          <p>
            <strong className="text-ink">گیرنده:</strong> {order.full_name}، <span dir="ltr">{faDigits(order.phone)}</span>
          </p>
          {order.address_line && (
            <p>
              <strong className="text-ink">نشانی:</strong> {order.province_name}، {order.city}، {order.address_line}
            </p>
          )}
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          {order.invoice_number && (
            <a
              href={`/api/v1/orders/${encodeURIComponent(order.number)}/invoice.pdf`}
              className="btn btn-secondary"
              target="_blank"
              rel="noopener"
            >
              دریافت رسید (PDF)
            </a>
          )}
        </div>
        {order.events.length > 0 && (
          <div className="mt-6">
            <h2 className="mb-3 text-sm font-bold text-ink">رویدادها</h2>
            <OrderTimeline order={order} />
          </div>
        )}
      </section>
    </div>
  );
}
