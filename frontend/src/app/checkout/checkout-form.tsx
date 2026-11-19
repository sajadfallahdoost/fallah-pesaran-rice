"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useCart } from "@/components/cart-context";
import { EmptyState } from "@/components/catalog";
import { AlertIcon, InfoIcon, ShieldIcon } from "@/components/icons";
import { api, ApiError, fieldError } from "@/lib/api-client";
import { faDigits, isValidMobile, normalizePhoneInput, toman, toLatinDigits } from "@/lib/format";
import { goToGateway } from "@/lib/payment-redirect";
import type { Address, PaymentProviderInfo, Province, Quote, ShippingOption } from "@/lib/types";

interface FormState {
  full_name: string;
  phone: string;
  email: string;
  province_id: string;
  city: string;
  address_line: string;
  postal_code: string;
  customer_note: string;
  save_address: boolean;
}

const EMPTY_FORM: FormState = {
  full_name: "",
  phone: "",
  email: "",
  province_id: "",
  city: "",
  address_line: "",
  postal_code: "",
  customer_note: "",
  save_address: true,
};

type Errors = Partial<Record<keyof FormState | "shipping_method_id" | "provider", string>>;

function newKey(): string {
  return crypto.randomUUID();
}

function validate(form: FormState, option: ShippingOption | undefined, provider: string): Errors {
  const errors: Errors = {};
  if (form.full_name.trim().length < 3) errors.full_name = "نام و نام خانوادگی گیرنده را کامل بنویسید.";
  if (!isValidMobile(form.phone)) errors.phone = "شمارهٔ موبایل معتبر نیست. نمونه: ۰۹۱۲۱۲۳۴۵۶۷";
  if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) errors.email = "ایمیل معتبر نیست.";
  if (!form.province_id) errors.province_id = "استان را انتخاب کنید.";
  if (form.city.trim().length < 2) errors.city = "شهر را بنویسید.";
  if (!option || option.requires_address) {
    if (form.address_line.trim().length < 10) errors.address_line = "نشانی را کامل‌تر بنویسید (خیابان، کوچه، پلاک، واحد).";
    const postal = toLatinDigits(form.postal_code).replace(/\D/g, "");
    if (postal && postal.length !== 10) errors.postal_code = "کد پستی باید ۱۰ رقم باشد.";
  }
  if (!option) errors.shipping_method_id = "روش ارسال را انتخاب کنید.";
  if (!provider) errors.provider = "درگاه پرداخت را انتخاب کنید.";
  return errors;
}

function Field({
  id,
  label,
  error,
  hint,
  optional,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  optional?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="field-label">
        {label}
        {optional && <span className="ms-1 text-xs font-normal text-ink-muted">(اختیاری)</span>}
      </label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="field-error">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="field-hint">
            {hint}
          </p>
        )
      )}
    </div>
  );
}

export function CheckoutForm() {
  const router = useRouter();
  const { cart: contextCart, loading: cartLoading, refresh: refreshCart } = useCart();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<Errors>({});
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [providers, setProviders] = useState<PaymentProviderInfo[]>([]);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [signedInPhone, setSignedInPhone] = useState<string | null>(null);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [quoting, setQuoting] = useState(false);
  const [methodId, setMethodId] = useState<number | null>(null);
  const [provider, setProvider] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState("");
  const idempotencyKey = useRef<string>("");
  const errorSummary = useRef<HTMLDivElement>(null);

  useEffect(() => {
    idempotencyKey.current = newKey();
    let cancelled = false;
    (async () => {
      const [provinceList, providerList, me] = await Promise.all([
        api<Province[]>("/shipping/provinces/").catch(() => []),
        api<PaymentProviderInfo[]>("/payments/providers/").catch(() => []),
        api<{ authenticated: boolean; phone?: string }>("/auth/me/").catch(() => ({ authenticated: false, phone: undefined })),
      ]);
      if (cancelled) return;
      setProvinces(provinceList);
      setProviders(providerList);
      setProvider((providerList.find((p) => p.is_default) ?? providerList[0])?.code ?? "");
      const tehran = provinceList.find((p) => p.name === "تهران");
      const tehranDefaults = tehran
        ? { province_id: String(tehran.id), city: "تهران" }
        : { province_id: "", city: "تهران" };
      if (me.authenticated && me.phone) {
        setSignedInPhone(me.phone);
        const saved = await api<Address[]>("/account/addresses/").catch(() => []);
        if (cancelled) return;
        setAddresses(saved);
        const preferred = saved.find((a) => a.is_default) ?? saved[0];
        setForm((current) => ({
          ...current,
          phone: current.phone || me.phone || "",
          ...(preferred
            ? {
                full_name: preferred.full_name,
                phone: preferred.phone,
                province_id: String(preferred.province_id),
                city: preferred.city,
                address_line: preferred.address_line,
                postal_code: preferred.postal_code,
                save_address: false,
              }
            : tehranDefaults),
        }));
      } else {
        setForm((current) => ({ ...current, ...tehranDefaults }));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const runQuote = useCallback(async (provinceId: string, city: string) => {
    setQuoting(true);
    try {
      const data = await api<Quote>("/checkout/quote/", {
        method: "POST",
        body: { province_id: provinceId ? Number(provinceId) : null, city: city.trim() },
      });
      setQuote(data);
      setMethodId((current) => {
        const available = data.shipping_options.filter((o) => o.available);
        if (current && available.some((o) => o.id === current)) return current;
        return available.length === 1 ? available[0].id : null;
      });
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "محاسبهٔ هزینهٔ ارسال انجام نشد.");
    } finally {
      setQuoting(false);
    }
  }, []);

  const destinationReady = Boolean(form.province_id) && form.city.trim().length >= 2;

  useEffect(() => {
    if (!destinationReady) return;
    const handle = setTimeout(() => void runQuote(form.province_id, form.city), 450);
    return () => clearTimeout(handle);
  }, [destinationReady, form.province_id, form.city, runQuote]);

  const cart = quote?.cart ?? contextCart;
  const options = quote?.shipping_options ?? [];
  const selected = options.find((o) => o.id === methodId && o.available);
  const totals = selected?.totals ?? null;
  const salesEnabled = quote?.sales_enabled ?? true;
  const anyTestProvider = useMemo(() => providers.some((p) => p.is_test), [providers]);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    if (errors[key]) setErrors((current) => ({ ...current, [key]: undefined }));
  }

  function applyAddress(id: string) {
    const address = addresses.find((a) => String(a.id) === id);
    if (!address) return;
    setForm((current) => ({
      ...current,
      full_name: address.full_name,
      phone: address.phone,
      province_id: String(address.province_id),
      city: address.city,
      address_line: address.address_line,
      postal_code: address.postal_code,
      save_address: false,
    }));
    setErrors({});
  }

  function showErrors(next: Errors, message: string) {
    setErrors(next);
    setFormError(message);
    requestAnimationFrame(() => errorSummary.current?.focus());
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFormError("");
    setNotice("");
    const clientErrors = validate(form, selected, provider);
    if (Object.keys(clientErrors).length) {
      showErrors(clientErrors, "لطفاً موارد مشخص‌شده را اصلاح کنید.");
      return;
    }
    if (!selected || !totals) return;
    setSubmitting(true);
    let placed: { number: string; token: string } | null = null;
    try {
      placed = await api<{ number: string; token: string; grand_total: number }>("/checkout/", {
        method: "POST",
        body: {
          full_name: form.full_name.trim(),
          phone: normalizePhoneInput(form.phone),
          email: form.email.trim(),
          province_id: Number(form.province_id),
          city: form.city.trim(),
          address_line: form.address_line.trim(),
          postal_code: toLatinDigits(form.postal_code).replace(/\D/g, ""),
          customer_note: form.customer_note.trim(),
          shipping_method_id: selected.id,
          idempotency_key: idempotencyKey.current,
          expected_total: totals.grand_total,
          save_address: Boolean(signedInPhone) && form.save_address,
        },
      });
    } catch (err) {
      setSubmitting(false);
      if (!(err instanceof ApiError)) {
        showErrors({}, "ثبت سفارش انجام نشد. دوباره تلاش کنید.");
        return;
      }
      if (err.code === "total_changed" || err.code === "cart_changed" || err.code === "shipping_unavailable") {
        idempotencyKey.current = newKey();
        await Promise.all([runQuote(form.province_id, form.city), refreshCart()]);
        setNotice(err.message);
        if (err.code === "cart_changed") router.push("/cart");
        return;
      }
      const fieldErrors: Errors = {};
      for (const key of Object.keys(form) as (keyof FormState)[]) {
        const message = fieldError(err, key);
        if (message) fieldErrors[key] = message;
      }
      const methodError = fieldError(err, "shipping_method_id");
      if (methodError) fieldErrors.shipping_method_id = methodError;
      showErrors(fieldErrors, err.message);
      return;
    }

    void refreshCart();
    const resultUrl = `/checkout/result/${encodeURIComponent(placed.number)}?t=${encodeURIComponent(placed.token)}`;
    try {
      await goToGateway(placed.number, placed.token, provider);
    } catch {
      // The order exists; the result page explains the state and lets the customer retry payment.
      router.replace(`${resultUrl}&start_failed=1`);
    }
  }

  if (cartLoading && !cart) {
    return (
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_24rem]" aria-busy="true">
        <div className="skeleton h-96" />
        <div className="skeleton h-72" />
      </div>
    );
  }

  if (!cart || cart.lines.length === 0) {
    return (
      <div className="mt-10">
        <EmptyState
          title="سبد خرید شما خالی است"
          description="برای ثبت سفارش ابتدا محصولی به سبد اضافه کنید."
          action={
            <Link href="/shop" className="btn btn-primary">
              مشاهدهٔ محصولات
            </Link>
          }
        />
      </div>
    );
  }

  const errorEntries = Object.entries(errors).filter(([, v]) => v);
  const inputProps = (key: keyof FormState) => ({
    id: key,
    name: key,
    "aria-invalid": errors[key] ? true : undefined,
    "aria-describedby": errors[key] ? `${key}-error` : undefined,
  });

  return (
    <form onSubmit={submit} noValidate className="mt-8 grid items-start gap-8 lg:grid-cols-[1fr_24rem]">
      <div className="flex flex-col gap-6">
        {(formError || notice) && (
          <div
            ref={errorSummary}
            tabIndex={-1}
            role="alert"
            className={`rounded-xl px-4 py-3 text-sm leading-7 ${
              formError ? "bg-danger-soft text-danger" : "bg-warn-soft text-gold-700"
            }`}
          >
            <p className="flex items-start gap-2 font-semibold">
              <AlertIcon size={18} className="mt-1 shrink-0" />
              {formError || notice}
            </p>
            {formError && errorEntries.length > 1 && (
              <ul className="ms-7 mt-1 list-disc">
                {errorEntries.map(([key, message]) => (
                  <li key={key}>
                    <a href={`#${key}`} className="underline">
                      {message}
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <section aria-labelledby="recipient" className="card p-5 sm:p-6">
          <h2 id="recipient" className="text-lg font-bold text-green-800">
            اطلاعات گیرنده
          </h2>
          {!signedInPhone && (
            <p className="mt-2 text-sm text-ink-muted">
              بدون ثبت‌نام خرید کنید، یا{" "}
              <Link href="/account?next=/checkout" className="font-semibold text-green-800 underline underline-offset-4">
                وارد حساب شوید
              </Link>{" "}
              تا نشانی‌ها و سفارش‌هایتان ذخیره شود.
            </p>
          )}
          {addresses.length > 0 && (
            <div className="mt-4">
              <label htmlFor="saved-address" className="field-label">
                نشانی‌های ذخیره‌شده
              </label>
              <select id="saved-address" className="field-input" defaultValue="" onChange={(e) => applyAddress(e.target.value)}>
                <option value="" disabled>
                  انتخاب نشانی
                </option>
                {addresses.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.label || a.full_name} — {a.city}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            <Field id="full_name" label="نام و نام خانوادگی" error={errors.full_name}>
              <input
                {...inputProps("full_name")}
                className="field-input"
                autoComplete="name"
                value={form.full_name}
                onChange={(e) => update("full_name", e.target.value)}
                maxLength={100}
              />
            </Field>
            <Field id="phone" label="شمارهٔ همراه" error={errors.phone} hint="برای هماهنگی ارسال و پیگیری سفارش">
              <input
                {...inputProps("phone")}
                className="field-input text-start"
                dir="ltr"
                inputMode="tel"
                autoComplete="tel"
                placeholder="09121234567"
                value={form.phone}
                onChange={(e) => update("phone", e.target.value)}
                maxLength={20}
              />
            </Field>
            <Field id="email" label="ایمیل" optional error={errors.email}>
              <input
                {...inputProps("email")}
                className="field-input text-start"
                dir="ltr"
                type="email"
                inputMode="email"
                autoComplete="email"
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                maxLength={254}
              />
            </Field>
          </div>
        </section>

        <section aria-labelledby="address" className="card p-5 sm:p-6">
          <h2 id="address" className="text-lg font-bold text-green-800">
            نشانی و روش ارسال
          </h2>
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            <Field id="province_id" label="استان" error={errors.province_id}>
              <select
                {...inputProps("province_id")}
                className="field-input"
                autoComplete="address-level1"
                value={form.province_id}
                onChange={(e) => update("province_id", e.target.value)}
              >
                <option value="">انتخاب استان</option>
                {provinces.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field id="city" label="شهر" error={errors.city}>
              <input
                {...inputProps("city")}
                className="field-input"
                autoComplete="address-level2"
                value={form.city}
                onChange={(e) => update("city", e.target.value)}
                maxLength={60}
              />
            </Field>
            <div className="sm:col-span-2">
              <Field id="address_line" label="نشانی کامل" error={errors.address_line} hint="خیابان، کوچه، پلاک و واحد">
                <textarea
                  {...inputProps("address_line")}
                  className="field-input min-h-24"
                  autoComplete="street-address"
                  value={form.address_line}
                  onChange={(e) => update("address_line", e.target.value)}
                  maxLength={300}
                />
              </Field>
            </div>
            <Field id="postal_code" label="کد پستی" optional error={errors.postal_code} hint="۱۰ رقم، بدون خط تیره">
              <input
                {...inputProps("postal_code")}
                className="field-input text-start"
                dir="ltr"
                inputMode="numeric"
                autoComplete="postal-code"
                value={form.postal_code}
                onChange={(e) => update("postal_code", e.target.value)}
                maxLength={12}
              />
            </Field>
            {signedInPhone && (
              <label className="flex items-center gap-2 self-end pb-3 text-sm">
                <input
                  type="checkbox"
                  checked={form.save_address}
                  onChange={(e) => update("save_address", e.target.checked)}
                  className="size-4 accent-green-800"
                />
                ذخیرهٔ این نشانی در حساب
              </label>
            )}
          </div>

          <fieldset className="mt-7" aria-describedby={errors.shipping_method_id ? "shipping-error" : undefined}>
            <legend className="field-label">روش ارسال</legend>
            {!destinationReady ? (
              <p className="rounded-xl bg-cream/70 px-4 py-3 text-sm text-ink-soft">
                برای دیدن روش‌ها و هزینهٔ ارسال، استان و شهر را وارد کنید.
              </p>
            ) : quoting && !quote ? (
              <div className="skeleton h-20" />
            ) : (
              <div className="flex flex-col gap-3" aria-busy={quoting}>
                {options.map((option) => (
                  <label
                    key={option.id}
                    className={`flex gap-3 rounded-xl border-[1.5px] px-4 py-3.5 ${
                      !option.available
                        ? "cursor-not-allowed border-line bg-cream/40 opacity-70"
                        : option.id === methodId
                          ? "cursor-pointer border-green-800 bg-green-50"
                          : "cursor-pointer border-line bg-white hover:border-green-700/50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="shipping_method"
                      value={option.id}
                      checked={option.id === methodId}
                      disabled={!option.available}
                      onChange={() => {
                        setMethodId(option.id);
                        setErrors((current) => ({ ...current, shipping_method_id: undefined }));
                      }}
                      className="mt-1.5 size-4 shrink-0 accent-green-800"
                    />
                    <span className="flex min-w-0 flex-1 flex-col gap-1">
                      <span className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-bold text-ink">{option.name}</span>
                        <span className="text-sm font-bold tabular text-green-800">
                          {!option.available
                            ? "در دسترس نیست"
                            : option.pay_on_delivery
                              ? "پس‌کرایه"
                              : option.is_free
                                ? "رایگان"
                                : toman(option.cost)}
                        </span>
                      </span>
                      {option.available ? (
                        <>
                          {option.delivery_estimate && (
                            <span className="text-sm text-ink-soft">{option.delivery_estimate}</span>
                          )}
                          {option.description && <span className="text-xs leading-6 text-ink-muted">{option.description}</span>}
                          {option.pay_on_delivery && (
                            <span className="text-xs leading-6 text-gold-700">
                              هزینهٔ ارسال هنگام تحویل به شرکت حمل پرداخت می‌شود و در مبلغ آنلاین نیست.
                            </span>
                          )}
                          {!option.is_free && option.free_threshold && option.free_threshold > (cart?.subtotal ?? 0) && (
                            <span className="text-xs text-success">
                              ارسال رایگان برای خرید بالای {toman(option.free_threshold)}
                            </span>
                          )}
                        </>
                      ) : (
                        option.unavailable_reason && <span className="text-xs text-ink-muted">{option.unavailable_reason}</span>
                      )}
                    </span>
                  </label>
                ))}
                {options.length === 0 && (
                  <p className="rounded-xl bg-warn-soft px-4 py-3 text-sm text-gold-700">
                    برای این مقصد روش ارسالی تعریف نشده است. لطفاً با فروشگاه تماس بگیرید.
                  </p>
                )}
              </div>
            )}
            {errors.shipping_method_id && (
              <p id="shipping-error" className="field-error">
                {errors.shipping_method_id}
              </p>
            )}
          </fieldset>

          <div className="mt-6">
            <Field id="customer_note" label="توضیح برای فروشگاه" optional>
              <textarea
                {...inputProps("customer_note")}
                className="field-input min-h-20"
                value={form.customer_note}
                onChange={(e) => update("customer_note", e.target.value)}
                maxLength={500}
              />
            </Field>
          </div>
        </section>

        <section aria-labelledby="payment" className="card p-5 sm:p-6">
          <h2 id="payment" className="text-lg font-bold text-green-800">
            پرداخت
          </h2>
          {providers.length === 0 ? (
            <p className="mt-4 rounded-xl bg-warn-soft px-4 py-3 text-sm text-gold-700">
              در حال حاضر درگاه پرداخت فعالی وجود ندارد. لطفاً بعداً تلاش کنید یا با فروشگاه تماس بگیرید.
            </p>
          ) : (
            <fieldset className="mt-4">
              <legend className="sr-only">انتخاب درگاه</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {providers.map((p) => (
                  <label
                    key={p.code}
                    className={`flex cursor-pointer gap-3 rounded-xl border-[1.5px] px-4 py-3.5 ${
                      provider === p.code ? "border-green-800 bg-green-50" : "border-line bg-white"
                    }`}
                  >
                    <input
                      type="radio"
                      name="provider"
                      value={p.code}
                      checked={provider === p.code}
                      onChange={() => setProvider(p.code)}
                      className="mt-1.5 size-4 shrink-0 accent-green-800"
                    />
                    <span>
                      <span className="block font-bold">{p.name}</span>
                      {p.description && <span className="block text-xs leading-6 text-ink-muted">{p.description}</span>}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}
          {anyTestProvider && (
            <p className="mt-4 flex items-start gap-2 rounded-xl bg-gold-100/70 px-4 py-3 text-sm leading-7 text-gold-700">
              <InfoIcon size={18} className="mt-1 shrink-0" />
              درگاه آزمایشی فقط برای نمایش است؛ هیچ پولی جابه‌جا نمی‌شود و سفارش واقعی ثبت نمی‌شود.
            </p>
          )}
          <p className="mt-4 flex items-start gap-2 text-sm leading-7 text-ink-soft">
            <ShieldIcon size={18} className="mt-1 shrink-0 text-green-800" />
            پس از ثبت سفارش به صفحهٔ درگاه بانک منتقل می‌شوید. شمارهٔ کارت، رمز دوم و CVV2 فقط در صفحهٔ بانک وارد
            می‌شود.
          </p>
        </section>
      </div>

      <aside className="lg:sticky lg:top-24" aria-label="خلاصهٔ سفارش">
        <div className="card p-5 sm:p-6">
          <h2 className="text-lg font-bold text-green-800">خلاصهٔ سفارش</h2>
          <ul className="mt-4 divide-y divide-line text-sm">
            {cart.lines.map((line) => (
              <li key={line.variant_id} className="flex justify-between gap-3 py-2.5">
                <span className="min-w-0">
                  <span className="block font-semibold">{line.product_name}</span>
                  <span className="block text-ink-muted">
                    {line.variant_title} × {faDigits(line.quantity)}
                  </span>
                </span>
                <span className="shrink-0 tabular">{toman(line.line_total)}</span>
              </li>
            ))}
          </ul>
          <dl className="mt-3 space-y-2.5 border-t border-line pt-4 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-ink-soft">مبلغ کالاها</dt>
              <dd className="tabular">{toman(totals?.merchandise_total ?? cart.merchandise_total)}</dd>
            </div>
            {(totals?.discount_total ?? cart.discount_total) > 0 && (
              <div className="flex justify-between gap-3 text-success">
                <dt>تخفیف</dt>
                <dd className="tabular">−{toman(totals?.discount_total ?? cart.discount_total)}</dd>
              </div>
            )}
            {totals && totals.tax_total > 0 && (
              <div className="flex justify-between gap-3">
                <dt className="text-ink-soft">مالیات بر ارزش افزوده</dt>
                <dd className="tabular">{toman(totals.tax_total)}</dd>
              </div>
            )}
            <div className="flex justify-between gap-3">
              <dt className="text-ink-soft">هزینهٔ ارسال</dt>
              <dd className="tabular">
                {!selected
                  ? "—"
                  : selected.pay_on_delivery
                    ? "پس‌کرایه"
                    : totals && totals.shipping_total > 0
                      ? toman(totals.shipping_total)
                      : "رایگان"}
              </dd>
            </div>
            <div className="flex justify-between gap-3 border-t border-line pt-3 text-base font-extrabold">
              <dt>مبلغ قابل پرداخت</dt>
              <dd className="tabular text-green-800">{totals ? toman(totals.grand_total) : "—"}</dd>
            </div>
          </dl>
          {!salesEnabled && (
            <p className="mt-4 rounded-xl bg-warn-soft px-4 py-3 text-sm text-gold-700" role="alert">
              ثبت سفارش موقتاً غیرفعال است.
            </p>
          )}
          <button
            type="submit"
            className="btn btn-primary mt-5 w-full"
            disabled={submitting || !salesEnabled || providers.length === 0 || cart.has_issues}
            aria-busy={submitting}
          >
            {submitting ? "در حال انتقال به درگاه…" : totals ? `ثبت سفارش و پرداخت ${toman(totals.grand_total)}` : "ثبت سفارش و پرداخت"}
          </button>
          <p className="mt-3 text-center text-xs leading-6 text-ink-muted">
            با ثبت سفارش،{" "}
            <Link href="/info/terms" className="underline">
              قوانین خرید
            </Link>{" "}
            و{" "}
            <Link href="/info/returns" className="underline">
              شرایط مرجوعی
            </Link>{" "}
            را می‌پذیرید.
          </p>
          <Link href="/cart" className="btn btn-ghost mt-2 w-full text-sm">
            بازگشت به سبد
          </Link>
        </div>
      </aside>
    </form>
  );
}
