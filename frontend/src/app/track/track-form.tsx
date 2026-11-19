"use client";

import { useState } from "react";

import { OrderItems, OrderProgress, OrderShipments, OrderTimeline, StageBadge } from "@/components/order-view";
import { api, ApiError } from "@/lib/api-client";
import { isValidMobile, jalaliDateTime, normalizePhoneInput, toLatinDigits } from "@/lib/format";
import type { OrderPublic } from "@/lib/types";

export function TrackForm() {
  const [number, setNumber] = useState("");
  const [phone, setPhone] = useState("");
  const [errors, setErrors] = useState<{ number?: string; phone?: string }>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [order, setOrder] = useState<OrderPublic | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const cleanNumber = toLatinDigits(number).trim().toUpperCase();
    const next: typeof errors = {};
    if (cleanNumber.length < 6) next.number = "شمارهٔ سفارش را کامل وارد کنید.";
    if (!isValidMobile(phone)) next.phone = "شمارهٔ موبایل معتبر نیست. نمونه: ۰۹۱۲۱۲۳۴۵۶۷";
    setErrors(next);
    setError("");
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      setOrder(
        await api<OrderPublic>("/orders/track/", {
          method: "POST",
          body: { number: cleanNumber, phone: normalizePhoneInput(phone) },
        }),
      );
    } catch (err) {
      setOrder(null);
      setError(err instanceof ApiError ? err.message : "پیگیری انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={submit} noValidate className="card grid gap-5 p-5 sm:grid-cols-[1fr_1fr_auto] sm:items-start sm:p-6">
        <div>
          <label htmlFor="number" className="field-label">
            شمارهٔ سفارش
          </label>
          <input
            id="number"
            className="field-input text-start font-mono"
            dir="ltr"
            placeholder="FS-…"
            value={number}
            onChange={(e) => setNumber(e.target.value)}
            aria-invalid={errors.number ? true : undefined}
            aria-describedby={errors.number ? "number-error" : undefined}
            autoComplete="off"
            maxLength={32}
          />
          {errors.number && (
            <p id="number-error" className="field-error">
              {errors.number}
            </p>
          )}
        </div>
        <div>
          <label htmlFor="phone" className="field-label">
            شمارهٔ همراه
          </label>
          <input
            id="phone"
            className="field-input text-start"
            dir="ltr"
            inputMode="tel"
            autoComplete="tel"
            placeholder="09121234567"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            aria-invalid={errors.phone ? true : undefined}
            aria-describedby={errors.phone ? "phone-error" : undefined}
            maxLength={20}
          />
          {errors.phone && (
            <p id="phone-error" className="field-error">
              {errors.phone}
            </p>
          )}
        </div>
        <button type="submit" className="btn btn-primary sm:mt-7" disabled={busy} aria-busy={busy}>
          {busy ? "در حال جست‌وجو…" : "پیگیری"}
        </button>
      </form>

      <div aria-live="polite">
        {error && (
          <p role="alert" className="rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
            {error}
          </p>
        )}
        {order && (
          <section className="card p-5 sm:p-6" aria-labelledby="tracked">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 id="tracked" className="text-lg font-bold text-green-800">
                سفارش <span dir="ltr" className="font-mono">{order.number}</span>
              </h2>
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
            {order.events.length > 0 && (
              <div className="mt-6">
                <h3 className="mb-3 text-sm font-bold text-ink">رویدادها</h3>
                <OrderTimeline order={order} />
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
