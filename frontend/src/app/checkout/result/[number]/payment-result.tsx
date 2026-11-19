"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AlertIcon, CheckIcon, ClockIcon, InfoIcon } from "@/components/icons";
import { OrderItems, OrderProgress, OrderTotals, StageBadge } from "@/components/order-view";
import { api, ApiError } from "@/lib/api-client";
import { faDigits, jalaliDateTime, toman } from "@/lib/format";
import { goToGateway } from "@/lib/payment-redirect";
import type { OrderPrivate, PaymentProviderInfo } from "@/lib/types";

// "redirected" means the customer left before the bank answered; the backend allows a fresh attempt then.
const PENDING_ATTEMPT = new Set(["unknown"]);
const MAX_POLLS = 6;

function Panel({
  tone,
  icon,
  title,
  children,
}: {
  tone: "ok" | "wait" | "bad";
  icon: React.ReactNode;
  title: string;
  children?: React.ReactNode;
}) {
  const colors = {
    ok: "border-success/30 bg-success-soft text-success",
    wait: "border-gold-500/40 bg-warn-soft text-gold-700",
    bad: "border-danger/30 bg-danger-soft text-danger",
  }[tone];
  return (
    <div className={`rounded-[var(--radius-card)] border px-5 py-6 sm:px-7 ${colors}`} role="status">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 shrink-0">{icon}</span>
        <div className="min-w-0">
          <h1 className="text-xl font-extrabold sm:text-2xl">{title}</h1>
          {children && <div className="mt-2 leading-8 text-ink-soft">{children}</div>}
        </div>
      </div>
    </div>
  );
}

export function PaymentResult({ number }: { number: string }) {
  const searchParams = useSearchParams();
  const token = searchParams.get("t") ?? "";
  const startFailed = searchParams.get("start_failed") === "1";
  const [order, setOrder] = useState<OrderPrivate | null>(null);
  const [loadError, setLoadError] = useState("");
  const [polls, setPolls] = useState(0);
  const [providers, setProviders] = useState<PaymentProviderInfo[]>([]);
  const [provider, setProvider] = useState("");
  const [paying, setPaying] = useState(false);
  const [payError, setPayError] = useState("");

  const load = useCallback(async () => {
    if (number === "unknown" || !token) {
      setLoadError("اطلاعات بازگشت از درگاه کامل نیست.");
      return;
    }
    try {
      setOrder(await api<OrderPrivate>(`/orders/${encodeURIComponent(number)}/?t=${encodeURIComponent(token)}`));
      setLoadError("");
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "دریافت وضعیت سفارش انجام نشد.");
    }
  }, [number, token]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch persisted order state once on mount
    void load();
  }, [load]);

  const attemptPending =
    order?.stage === "awaiting_payment" && order.latest_payment && PENDING_ATTEMPT.has(order.latest_payment.status);

  useEffect(() => {
    if (!attemptPending || polls >= MAX_POLLS) return;
    const handle = setTimeout(() => {
      setPolls((n) => n + 1);
      void load();
    }, 5000);
    return () => clearTimeout(handle);
  }, [attemptPending, polls, load]);

  useEffect(() => {
    if (!order?.can_pay) return;
    let cancelled = false;
    api<PaymentProviderInfo[]>("/payments/providers/")
      .then((list) => {
        if (cancelled) return;
        setProviders(list);
        setProvider((current) => current || (list.find((p) => p.is_default) ?? list[0])?.code || "");
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [order?.can_pay]);

  async function retryPayment() {
    if (!order || !provider) return;
    setPaying(true);
    setPayError("");
    try {
      await goToGateway(order.number, token, provider);
    } catch (err) {
      setPayError(err instanceof ApiError ? err.message : "اتصال به درگاه انجام نشد.");
      setPaying(false);
      void load();
    }
  }

  if (loadError) {
    return (
      <Panel tone="bad" icon={<AlertIcon size={28} />} title="وضعیت سفارش نمایش داده نشد">
        <p>{loadError}</p>
        <p className="mt-2">
          اگر مبلغی از حساب شما کم شده است، با شمارهٔ سفارش از صفحهٔ{" "}
          <Link href="/track" className="font-semibold text-green-800 underline">
            پیگیری سفارش
          </Link>{" "}
          وضعیت را ببینید یا با فروشگاه تماس بگیرید.
        </p>
      </Panel>
    );
  }

  if (!order) return <div className="skeleton h-80" aria-busy="true" aria-label="در حال دریافت وضعیت" />;

  const paid = order.payment_status === "paid" || Boolean(order.paid_at);
  const latest = order.latest_payment;
  const invoiceUrl = `/api/v1/orders/${encodeURIComponent(order.number)}/invoice.pdf?t=${encodeURIComponent(token)}`;

  let panel: React.ReactNode;
  if (paid && (order.stage === "canceled" || order.stage === "returned")) {
    panel = (
      <Panel tone="bad" icon={<InfoIcon size={28} />} title={order.stage === "canceled" ? "سفارش لغو شده است" : "سفارش مرجوع شده است"}>
        <p>وضعیت پرداخت: {order.payment_status_label}. برای جزئیات بازپرداخت با فروشگاه در تماس باشید.</p>
      </Panel>
    );
  } else if (paid) {
    panel = (
      <Panel
        tone={order.stage === "under_review" ? "wait" : "ok"}
        icon={<CheckIcon size={28} />}
        title={order.stage === "under_review" ? "پرداخت ثبت شد؛ سفارش در حال بررسی است" : "پرداخت با موفقیت تأیید شد"}
      >
        <p>
          سفارش <strong className="font-mono text-ink" dir="ltr">{order.number}</strong> ثبت شد.
          {latest?.reference_number && (
            <>
              {" "}
              کد پیگیری بانک: <strong className="font-mono text-ink" dir="ltr">{latest.reference_number}</strong>
            </>
          )}
        </p>
        {order.stage === "under_review" && (
          <p className="mt-1">فروشگاه پیش از ارسال با شما تماس می‌گیرد. نیازی به پرداخت دوباره نیست.</p>
        )}
        {order.is_test && <p className="mt-1 text-sm">این سفارش با درگاه آزمایشی پرداخت شده و واقعی نیست.</p>}
      </Panel>
    );
  } else if (attemptPending && polls < MAX_POLLS) {
    panel = (
      <Panel tone="wait" icon={<ClockIcon size={28} />} title="در حال استعلام نتیجهٔ پرداخت از بانک…">
        <p>این صفحه را نبندید. نتیجه چند لحظهٔ دیگر به‌روز می‌شود.</p>
      </Panel>
    );
  } else if (attemptPending) {
    panel = (
      <Panel tone="wait" icon={<ClockIcon size={28} />} title="نتیجهٔ پرداخت هنوز مشخص نیست">
        <p>
          اگر مبلغی از حساب شما کم شده است، دوباره پرداخت نکنید. فروشگاه به‌طور خودکار وضعیت را از بانک استعلام
          می‌کند و در صورت عدم تأیید، بانک مبلغ را طبق ضوابط خود بازمی‌گرداند.
        </p>
        <button type="button" className="btn btn-secondary mt-4" onClick={() => { setPolls(0); void load(); }}>
          بررسی دوباره
        </button>
      </Panel>
    );
  } else if (order.stage === "expired" || order.stage === "canceled") {
    panel = (
      <Panel tone="bad" icon={<AlertIcon size={28} />} title={order.stage === "expired" ? "مهلت پرداخت تمام شد" : "سفارش لغو شده است"}>
        <p>این سفارش پرداخت نشده است. برای خرید، دوباره محصولات را به سبد اضافه کنید.</p>
        <Link href="/shop" className="btn btn-primary mt-4">
          بازگشت به فروشگاه
        </Link>
      </Panel>
    );
  } else {
    const canceled = latest?.status === "canceled";
    panel = (
      <Panel
        tone="bad"
        icon={<AlertIcon size={28} />}
        title={startFailed ? "اتصال به درگاه برقرار نشد" : canceled ? "پرداخت لغو شد" : "پرداخت ناموفق بود"}
      >
        <p>
          سفارش شما ثبت شده و کالاها تا {jalaliDateTime(order.reservation_expires_at)} برایتان نگه داشته می‌شود. می‌توانید
          دوباره پرداخت کنید.
        </p>
        <p className="mt-1 text-sm">اگر مبلغی از حسابتان کم شده، پیش از پرداخت دوباره چند دقیقه صبر کنید یا با فروشگاه تماس بگیرید.</p>
      </Panel>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {panel}

      {order.can_pay && !attemptPending && (
        <section className="card p-5 sm:p-6" aria-labelledby="retry">
          <h2 id="retry" className="text-lg font-bold text-green-800">
            پرداخت {toman(order.grand_total)}
          </h2>
          {providers.length > 1 && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {providers.map((p) => (
                <label
                  key={p.code}
                  className={`flex cursor-pointer items-center gap-3 rounded-xl border-[1.5px] px-4 py-3 ${
                    provider === p.code ? "border-green-800 bg-green-50" : "border-line bg-white"
                  }`}
                >
                  <input
                    type="radio"
                    name="provider"
                    value={p.code}
                    checked={provider === p.code}
                    onChange={() => setProvider(p.code)}
                    className="size-4 accent-green-800"
                  />
                  <span className="font-semibold">{p.name}</span>
                </label>
              ))}
            </div>
          )}
          {payError && (
            <p role="alert" className="mt-4 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
              {payError}
            </p>
          )}
          <button
            type="button"
            className="btn btn-primary mt-5 w-full sm:w-auto"
            onClick={retryPayment}
            disabled={paying || !provider}
            aria-busy={paying}
          >
            {paying ? "در حال انتقال به درگاه…" : "پرداخت دوباره"}
          </button>
        </section>
      )}

      <section className="card p-5 sm:p-6" aria-labelledby="order-summary">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="order-summary" className="text-lg font-bold text-green-800">
            سفارش <span dir="ltr" className="font-mono">{order.number}</span>
          </h2>
          <StageBadge stage={order.stage} />
        </div>
        {paid && (
          <div className="mt-6">
            <OrderProgress stage={order.stage} />
          </div>
        )}
        <div className="mt-5">
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
          {order.shipping_estimate && (
            <p>
              <strong className="text-ink">زمان ارسال:</strong> {order.shipping_estimate}
            </p>
          )}
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          {order.invoice_number && (
            <a href={invoiceUrl} className="btn btn-secondary" target="_blank" rel="noopener">
              دریافت رسید (PDF)
            </a>
          )}
          <Link href="/track" className="btn btn-ghost">
            پیگیری سفارش
          </Link>
        </div>
        <p className="mt-4 flex items-start gap-2 text-xs leading-6 text-ink-muted">
          <InfoIcon size={16} className="mt-0.5 shrink-0" />
          شمارهٔ سفارش را نگه دارید. برای پیگیری بعدی، شمارهٔ سفارش و شمارهٔ همراه کافی است.
        </p>
      </section>
    </div>
  );
}
