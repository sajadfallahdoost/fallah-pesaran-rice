"use client";

import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api-client";
import { faDigits, isValidMobile, normalizePhoneInput, toLatinDigits } from "@/lib/format";

export function LoginForm({ onSuccess }: { onSuccess: () => void | Promise<void> }) {
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const codeInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const handle = setTimeout(() => setCooldown((s) => s - 1), 1000);
    return () => clearTimeout(handle);
  }, [cooldown]);

  useEffect(() => {
    if (step === "code") codeInput.current?.focus();
  }, [step]);

  async function requestCode(event?: React.FormEvent) {
    event?.preventDefault();
    setError("");
    if (!isValidMobile(phone)) {
      setError("شمارهٔ موبایل معتبر نیست. نمونه: ۰۹۱۲۱۲۳۴۵۶۷");
      return;
    }
    setBusy(true);
    try {
      await api("/auth/otp/request/", { method: "POST", body: { phone: normalizePhoneInput(phone) } });
      setStep("code");
      setCode("");
      setCooldown(60);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "ارسال کد انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  async function verify(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    const clean = toLatinDigits(code).replace(/\D/g, "");
    if (clean.length < 4) {
      setError("کد پیامک‌شده را وارد کنید.");
      return;
    }
    setBusy(true);
    try {
      await api("/auth/otp/verify/", { method: "POST", body: { phone: normalizePhoneInput(phone), code: clean } });
      await onSuccess();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "ورود انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card p-5 sm:p-6">
      <h2 className="text-lg font-bold text-green-800">ورود با شمارهٔ همراه</h2>
      {step === "phone" ? (
        <form onSubmit={requestCode} noValidate className="mt-5 flex flex-col gap-4">
          <div>
            <label htmlFor="login-phone" className="field-label">
              شمارهٔ همراه
            </label>
            <input
              id="login-phone"
              className="field-input text-start"
              dir="ltr"
              inputMode="tel"
              autoComplete="tel"
              placeholder="09121234567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "login-error" : "login-hint"}
              maxLength={20}
            />
            <p id="login-hint" className="field-hint">
              یک کد یک‌بارمصرف برایتان پیامک می‌شود.
            </p>
          </div>
          {error && (
            <p id="login-error" role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}
          <button type="submit" className="btn btn-primary" disabled={busy} aria-busy={busy}>
            {busy ? "در حال ارسال…" : "دریافت کد"}
          </button>
        </form>
      ) : (
        <form onSubmit={verify} noValidate className="mt-5 flex flex-col gap-4">
          <p className="text-sm text-ink-soft">
            کد به شمارهٔ <span dir="ltr" className="font-semibold">{faDigits(normalizePhoneInput(phone))}</span> پیامک شد.{" "}
            <button type="button" className="font-semibold text-green-800 underline" onClick={() => setStep("phone")}>
              تغییر شماره
            </button>
          </p>
          <div>
            <label htmlFor="login-code" className="field-label">
              کد تأیید
            </label>
            <input
              ref={codeInput}
              id="login-code"
              className="field-input text-center text-lg tracking-[0.5em]"
              dir="ltr"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "code-error" : undefined}
              maxLength={6}
            />
          </div>
          {error && (
            <p id="code-error" role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}
          <button type="submit" className="btn btn-primary" disabled={busy} aria-busy={busy}>
            {busy ? "در حال بررسی…" : "ورود"}
          </button>
          <button
            type="button"
            className="btn btn-ghost text-sm"
            onClick={() => requestCode()}
            disabled={busy || cooldown > 0}
          >
            {cooldown > 0 ? `ارسال دوباره تا ${faDigits(cooldown)} ثانیهٔ دیگر` : "ارسال دوبارهٔ کد"}
          </button>
        </form>
      )}
    </div>
  );
}
