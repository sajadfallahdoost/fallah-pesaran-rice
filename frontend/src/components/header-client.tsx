"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useCart } from "@/components/cart-context";
import { CartIcon, CheckIcon, CloseIcon, MenuIcon, PhoneIcon } from "@/components/icons";
import { faDigits, PHONE_DISPLAY, PHONE_HREF } from "@/lib/format";

export function CartButton() {
  const { count } = useCart();
  return (
    <Link
      href="/cart"
      className="relative inline-flex size-11 items-center justify-center rounded-xl text-green-800 hover:bg-green-50"
      aria-label={count ? `سبد خرید، ${faDigits(count)} قلم` : "سبد خرید خالی است"}
    >
      <CartIcon />
      {count > 0 && (
        <span className="absolute -top-0.5 -start-0.5 min-w-5 rounded-full bg-gold-500 px-1 text-center text-xs font-bold leading-5 text-green-950 tabular">
          {faDigits(count)}
        </span>
      )}
    </Link>
  );
}

export function CartToast() {
  const { announcement } = useCart();
  return (
    <div aria-live="polite" role="status" className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex justify-center px-4">
      {announcement && (
        <div className="pointer-events-auto flex items-center gap-3 rounded-2xl bg-green-900 px-4 py-3 text-sm text-rice shadow-lg">
          <CheckIcon size={18} className="text-gold-200" />
          <span>{announcement}</span>
          <Link href="/cart" className="font-semibold text-gold-200 underline underline-offset-4">
            مشاهدهٔ سبد
          </Link>
        </div>
      )}
    </div>
  );
}

interface NavItem {
  href: string;
  label: string;
}

export function NavLink({ href, label }: NavItem) {
  const pathname = usePathname();
  const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`rounded-lg px-3 py-2 text-[0.95rem] transition-colors hover:text-green-800 ${
        active ? "font-semibold text-green-800" : "text-ink-soft"
      }`}
    >
      {label}
    </Link>
  );
}

export function MobileMenu({ items, phone }: { items: NavItem[]; phone: string }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const closeRef = useRef<HTMLButtonElement>(null);
  const [lastPath, setLastPath] = useState(pathname);

  if (pathname !== lastPath) {
    setLastPath(pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        className="inline-flex size-11 shrink-0 items-center justify-center rounded-xl text-green-800 hover:bg-green-50 lg:hidden"
        aria-label="باز کردن منو"
        aria-expanded={open}
        aria-controls="mobile-menu"
        onClick={() => setOpen(true)}
      >
        <MenuIcon />
      </button>
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="منوی سایت" id="mobile-menu">
          <button
            type="button"
            className="absolute inset-0 bg-green-950/40"
            aria-label="بستن منو"
            tabIndex={-1}
            onClick={() => setOpen(false)}
          />
          <nav className="absolute inset-y-0 start-0 flex w-[min(20rem,85vw)] flex-col bg-rice shadow-2xl">
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <span className="font-bold text-green-800">فلاح و پسران</span>
              <button
                ref={closeRef}
                type="button"
                className="inline-flex size-11 items-center justify-center rounded-xl hover:bg-green-50"
                aria-label="بستن منو"
                onClick={() => setOpen(false)}
              >
                <CloseIcon />
              </button>
            </div>
            <ul className="flex-1 overflow-y-auto px-2 py-3">
              {items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="flex min-h-12 items-center rounded-xl px-3 text-base text-ink hover:bg-green-50"
                    aria-current={pathname === item.href ? "page" : undefined}
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
            <a href={PHONE_HREF(phone)} className="m-4 btn btn-secondary">
              <PhoneIcon size={18} />
              <span dir="ltr">{PHONE_DISPLAY(phone)}</span>
            </a>
          </nav>
        </div>
      )}
    </>
  );
}
