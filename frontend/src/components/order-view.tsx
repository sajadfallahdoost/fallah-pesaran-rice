import { CheckIcon } from "@/components/icons";
import { faDigits, jalaliDateTime, toman } from "@/lib/format";
import type { OrderPrivate, OrderPublic, OrderStage } from "@/lib/types";

const STAGE_TEXT: Record<OrderStage, { title: string; tone: "ok" | "wait" | "bad" }> = {
  awaiting_payment: { title: "در انتظار پرداخت", tone: "wait" },
  under_review: { title: "پرداخت‌شده، در حال بررسی فروشگاه", tone: "wait" },
  unfulfilled: { title: "پرداخت‌شده، در صف آماده‌سازی", tone: "ok" },
  preparing: { title: "در حال آماده‌سازی", tone: "ok" },
  shipped: { title: "ارسال شده", tone: "ok" },
  delivered: { title: "تحویل شده", tone: "ok" },
  canceled: { title: "لغو شده", tone: "bad" },
  expired: { title: "منقضی شده (پرداخت انجام نشد)", tone: "bad" },
  returned: { title: "مرجوع شده", tone: "bad" },
};

const STEPS: { stage: OrderStage; label: string }[] = [
  { stage: "unfulfilled", label: "ثبت و پرداخت" },
  { stage: "preparing", label: "آماده‌سازی" },
  { stage: "shipped", label: "ارسال" },
  { stage: "delivered", label: "تحویل" },
];

export function stageInfo(stage: OrderStage) {
  return STAGE_TEXT[stage] ?? { title: stage, tone: "wait" as const };
}

export function StageBadge({ stage }: { stage: OrderStage }) {
  const info = stageInfo(stage);
  const tone =
    info.tone === "ok"
      ? "bg-success-soft text-success"
      : info.tone === "bad"
        ? "bg-danger-soft text-danger"
        : "bg-warn-soft text-gold-700";
  return <span className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${tone}`}>{info.title}</span>;
}

export function OrderProgress({ stage }: { stage: OrderStage }) {
  const index = STEPS.findIndex((s) => s.stage === (stage === "under_review" ? "unfulfilled" : stage));
  if (index < 0) return null;
  return (
    <ol className="grid grid-cols-4 gap-2" aria-label="مراحل سفارش">
      {STEPS.map((step, i) => {
        const done = i <= index;
        return (
          <li key={step.stage} className="flex flex-col items-center gap-2 text-center">
            <span
              className={`flex size-9 items-center justify-center rounded-full border-2 text-sm font-bold ${
                done ? "border-green-800 bg-green-800 text-rice" : "border-line bg-white text-ink-muted"
              }`}
              aria-hidden="true"
            >
              {done ? <CheckIcon size={16} /> : faDigits(i + 1)}
            </span>
            <span className={`text-xs sm:text-sm ${done ? "font-semibold text-green-800" : "text-ink-muted"}`}>
              {step.label}
              <span className="sr-only">{done ? " (انجام شده)" : ""}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function OrderItems({ order }: { order: OrderPublic }) {
  return (
    <ul className="divide-y divide-line text-sm">
      {order.items.map((item) => (
        <li key={item.sku} className="flex justify-between gap-3 py-3">
          <span className="min-w-0">
            <span className="block font-semibold">{item.product_name}</span>
            <span className="block text-ink-muted">
              {item.variant_title} × {faDigits(item.quantity)}
            </span>
          </span>
          <span className="shrink-0 tabular">{toman(item.line_total)}</span>
        </li>
      ))}
    </ul>
  );
}

export function OrderTotals({ order }: { order: OrderPrivate }) {
  return (
    <dl className="space-y-2.5 text-sm">
      <div className="flex justify-between gap-3">
        <dt className="text-ink-soft">مبلغ کالاها</dt>
        <dd className="tabular">{toman(order.merchandise_total)}</dd>
      </div>
      {order.discount_total > 0 && (
        <div className="flex justify-between gap-3 text-success">
          <dt>تخفیف</dt>
          <dd className="tabular">−{toman(order.discount_total)}</dd>
        </div>
      )}
      {order.tax_total > 0 && (
        <div className="flex justify-between gap-3">
          <dt className="text-ink-soft">مالیات بر ارزش افزوده</dt>
          <dd className="tabular">{toman(order.tax_total)}</dd>
        </div>
      )}
      <div className="flex justify-between gap-3">
        <dt className="text-ink-soft">ارسال ({order.shipping_method_name})</dt>
        <dd className="tabular">
          {order.shipping_on_delivery ? "پس‌کرایه" : order.shipping_total > 0 ? toman(order.shipping_total) : "رایگان"}
        </dd>
      </div>
      <div className="flex justify-between gap-3 border-t border-line pt-3 text-base font-extrabold">
        <dt>مبلغ کل</dt>
        <dd className="tabular text-green-800">{toman(order.grand_total)}</dd>
      </div>
    </dl>
  );
}

export function OrderShipments({ order }: { order: OrderPublic }) {
  if (order.shipments.length === 0) return null;
  return (
    <div className="space-y-3">
      {order.shipments.map((shipment, index) => (
        <div key={index} className="rounded-xl border border-line bg-white px-4 py-3 text-sm">
          <p className="font-semibold">
            {shipment.status_label}
            {shipment.carrier ? ` — ${shipment.carrier}` : ""}
          </p>
          {shipment.tracking_code && (
            <p className="mt-1 text-ink-soft">
              کد رهگیری:{" "}
              <span dir="ltr" className="font-mono">
                {shipment.tracking_code}
              </span>
            </p>
          )}
          {shipment.tracking_url && /^https:\/\//.test(shipment.tracking_url) && (
            <a
              href={shipment.tracking_url}
              rel="noopener noreferrer nofollow"
              target="_blank"
              className="mt-1 inline-block font-semibold text-green-800 underline"
            >
              پیگیری در سایت شرکت حمل
            </a>
          )}
          {shipment.shipped_at && <p className="mt-1 text-xs text-ink-muted">ارسال: {jalaliDateTime(shipment.shipped_at)}</p>}
        </div>
      ))}
    </div>
  );
}

export function OrderTimeline({ order }: { order: OrderPublic }) {
  if (order.events.length === 0) return null;
  return (
    <ol className="space-y-3 border-s-2 border-line ps-4 text-sm">
      {order.events.map((event, index) => (
        <li key={index}>
          <p>{event.message}</p>
          <p className="text-xs text-ink-muted">{jalaliDateTime(event.created_at)}</p>
        </li>
      ))}
    </ol>
  );
}
