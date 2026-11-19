/** All amounts from the API are integer rials. The storefront shows toman (rial ÷ 10). */

const faNumber = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 0, useGrouping: true });

export function toman(rial: number): string {
  return `${faNumber.format(Math.round(rial / 10))} تومان`;
}

export function tomanNumber(rial: number): string {
  return faNumber.format(Math.round(rial / 10));
}

export function faDigits(value: string | number): string {
  return String(value).replace(/[0-9]/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[Number(d)]);
}

export function toLatinDigits(value: string): string {
  return value
    .replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)))
    .replace(/[٠-٩]/g, (d) => String("٠١٢٣٤٥٦٧٨٩".indexOf(d)));
}

const dateFormatter = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
  year: "numeric",
  month: "long",
  day: "numeric",
  timeZone: "Asia/Tehran",
});
const dateTimeFormatter = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
  year: "numeric",
  month: "long",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Asia/Tehran",
});

export function jalaliDate(iso: string): string {
  return dateFormatter.format(new Date(iso));
}

export function jalaliDateTime(iso: string): string {
  return dateTimeFormatter.format(new Date(iso));
}

export function normalizePhoneInput(raw: string): string {
  let digits = toLatinDigits(raw).replace(/\D/g, "");
  if (digits.startsWith("0098")) digits = digits.slice(4);
  else if (digits.startsWith("98") && digits.length === 12) digits = digits.slice(2);
  if (digits.length === 10 && digits.startsWith("9")) digits = `0${digits}`;
  return digits;
}

export function isValidMobile(raw: string): boolean {
  return /^09\d{9}$/.test(normalizePhoneInput(raw));
}

export const PHONE_DISPLAY = (latin: string) => faDigits(latin);
export const PHONE_HREF = (latin: string) => `tel:+98${latin.replace(/^0/, "")}`;
