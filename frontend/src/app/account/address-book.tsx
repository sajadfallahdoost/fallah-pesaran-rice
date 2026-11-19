"use client";

import { useEffect, useState } from "react";

import { api, ApiError, fieldError } from "@/lib/api-client";
import { faDigits, normalizePhoneInput, toLatinDigits } from "@/lib/format";
import type { Address, Province } from "@/lib/types";

type Draft = Omit<Address, "id" | "province_name" | "province_id"> & { province_id: string };

const EMPTY: Draft = {
  label: "",
  full_name: "",
  phone: "",
  province_id: "",
  city: "",
  address_line: "",
  postal_code: "",
  is_default: false,
};

const FIELDS = ["label", "full_name", "phone", "province_id", "city", "address_line", "postal_code"] as const;

export function AddressBook() {
  const [addresses, setAddresses] = useState<Address[] | null>(null);
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function reload() {
    setAddresses(await api<Address[]>("/account/addresses/").catch(() => []));
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api<Address[]>("/account/addresses/").catch(() => []),
      api<Province[]>("/shipping/provinces/").catch(() => []),
    ]).then(([list, provinceList]) => {
      if (cancelled) return;
      setAddresses(list);
      setProvinces(provinceList);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  function startEdit(address?: Address) {
    setErrors({});
    setError("");
    if (address) {
      const { id, province_name, ...rest } = address;
      void province_name;
      setDraft({ ...rest, province_id: String(rest.province_id) });
      setEditing(id);
    } else {
      setDraft({ ...EMPTY, is_default: (addresses?.length ?? 0) === 0 });
      setEditing("new");
    }
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    setError("");
    const body = {
      ...draft,
      province_id: draft.province_id ? Number(draft.province_id) : null,
      phone: normalizePhoneInput(draft.phone),
      postal_code: toLatinDigits(draft.postal_code).replace(/\D/g, ""),
    };
    try {
      if (editing === "new") await api("/account/addresses/", { method: "POST", body });
      else await api(`/account/addresses/${editing}/`, { method: "PATCH", body });
      setEditing(null);
      await reload();
    } catch (err) {
      const next: Record<string, string> = {};
      for (const key of FIELDS) {
        const message = fieldError(err, key);
        if (message) next[key] = message;
      }
      setErrors(next);
      setError(err instanceof ApiError ? err.message : "ذخیرهٔ نشانی انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!window.confirm("این نشانی حذف شود؟")) return;
    await api(`/account/addresses/${id}/`, { method: "DELETE" }).catch(() => undefined);
    await reload();
  }

  if (addresses === null) return <div className="skeleton h-40" />;

  if (editing !== null) {
    const input = (key: (typeof FIELDS)[number]) => ({
      id: `addr-${key}`,
      "aria-invalid": errors[key] ? true : undefined,
      "aria-describedby": errors[key] ? `addr-${key}-error` : undefined,
    });
    const err = (key: string) =>
      errors[key] && (
        <p id={`addr-${key}-error`} className="field-error">
          {errors[key]}
        </p>
      );
    return (
      <form onSubmit={save} noValidate className="card grid gap-5 p-5 sm:grid-cols-2 sm:p-6">
        <h2 className="text-lg font-bold text-green-800 sm:col-span-2">
          {editing === "new" ? "نشانی جدید" : "ویرایش نشانی"}
        </h2>
        {error && (
          <p role="alert" className="rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger sm:col-span-2">
            {error}
          </p>
        )}
        <div>
          <label htmlFor="addr-label" className="field-label">
            عنوان <span className="text-xs font-normal text-ink-muted">(مثلاً خانه)</span>
          </label>
          <input {...input("label")} className="field-input" value={draft.label} onChange={(e) => setDraft({ ...draft, label: e.target.value })} maxLength={40} />
          {err("label")}
        </div>
        <div>
          <label htmlFor="addr-full_name" className="field-label">
            نام گیرنده
          </label>
          <input {...input("full_name")} className="field-input" autoComplete="name" value={draft.full_name} onChange={(e) => setDraft({ ...draft, full_name: e.target.value })} maxLength={100} />
          {err("full_name")}
        </div>
        <div>
          <label htmlFor="addr-phone" className="field-label">
            شمارهٔ همراه گیرنده
          </label>
          <input {...input("phone")} className="field-input text-start" dir="ltr" inputMode="tel" autoComplete="tel" value={draft.phone} onChange={(e) => setDraft({ ...draft, phone: e.target.value })} maxLength={20} />
          {err("phone")}
        </div>
        <div>
          <label htmlFor="addr-province_id" className="field-label">
            استان
          </label>
          <select {...input("province_id")} className="field-input" value={draft.province_id} onChange={(e) => setDraft({ ...draft, province_id: e.target.value })}>
            <option value="">انتخاب استان</option>
            {provinces.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {err("province_id")}
        </div>
        <div>
          <label htmlFor="addr-city" className="field-label">
            شهر
          </label>
          <input {...input("city")} className="field-input" value={draft.city} onChange={(e) => setDraft({ ...draft, city: e.target.value })} maxLength={60} />
          {err("city")}
        </div>
        <div>
          <label htmlFor="addr-postal_code" className="field-label">
            کد پستی <span className="text-xs font-normal text-ink-muted">(اختیاری)</span>
          </label>
          <input {...input("postal_code")} className="field-input text-start" dir="ltr" inputMode="numeric" value={draft.postal_code} onChange={(e) => setDraft({ ...draft, postal_code: e.target.value })} maxLength={12} />
          {err("postal_code")}
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="addr-address_line" className="field-label">
            نشانی کامل
          </label>
          <textarea {...input("address_line")} className="field-input min-h-24" value={draft.address_line} onChange={(e) => setDraft({ ...draft, address_line: e.target.value })} maxLength={300} />
          {err("address_line")}
        </div>
        <label className="flex items-center gap-2 text-sm sm:col-span-2">
          <input type="checkbox" checked={draft.is_default} onChange={(e) => setDraft({ ...draft, is_default: e.target.checked })} className="size-4 accent-green-800" />
          نشانی پیش‌فرض
        </label>
        <div className="flex flex-wrap gap-3 sm:col-span-2">
          <button type="submit" className="btn btn-primary" disabled={busy} aria-busy={busy}>
            ذخیره
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => setEditing(null)}>
            انصراف
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {addresses.length === 0 && (
        <p className="rounded-[var(--radius-card)] border border-dashed border-line p-8 text-center text-ink-soft">
          هنوز نشانی ذخیره نکرده‌اید.
        </p>
      )}
      {addresses.map((address) => (
        <div key={address.id} className="card flex flex-wrap items-start justify-between gap-3 p-4 sm:p-5">
          <div className="min-w-0 text-sm leading-7">
            <p className="font-bold text-ink">
              {address.label || address.full_name}
              {address.is_default && (
                <span className="ms-2 rounded-full bg-green-50 px-2 py-0.5 text-xs font-semibold text-green-800">پیش‌فرض</span>
              )}
            </p>
            <p className="text-ink-soft">
              {address.province_name}، {address.city}، {address.address_line}
            </p>
            <p className="text-ink-muted">
              {address.full_name} · <span dir="ltr">{faDigits(address.phone)}</span>
            </p>
          </div>
          <div className="flex gap-1">
            <button type="button" className="btn btn-ghost min-h-10 px-3 text-sm" onClick={() => startEdit(address)}>
              ویرایش
            </button>
            <button type="button" className="btn btn-ghost min-h-10 px-3 text-sm text-danger" onClick={() => remove(address.id)}>
              حذف
            </button>
          </div>
        </div>
      ))}
      {addresses.length < 10 && (
        <button type="button" className="btn btn-secondary self-start" onClick={() => startEdit()}>
          افزودن نشانی
        </button>
      )}
    </div>
  );
}
