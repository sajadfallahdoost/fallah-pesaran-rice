import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { Suspense } from "react";

import { CartProvider } from "@/components/cart-context";
import { CartToast } from "@/components/header-client";
import { Footer, Header, HeaderFallback } from "@/components/site-chrome";
import { SITE_URL } from "@/lib/seo";

import "./globals.css";

const vazirmatn = localFont({
  src: "../fonts/Vazirmatn-Variable.woff2",
  variable: "--font-vazirmatn",
  weight: "100 900",
  display: "swap",
  preload: true,
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "فلاح و پسران | خرید آنلاین برنج ایرانی، چای و روغن زیتون",
    template: "%s | فلاح و پسران",
  },
  description:
    "فروشگاه آنلاین فلاح و پسران: برنج ایرانی در بسته‌های خانوادگی با قیمت هر کیلو، چای و روغن زیتون؛ هزینهٔ ارسال پیش از پرداخت مشخص است.",
  applicationName: "فلاح و پسران",
  openGraph: {
    type: "website",
    locale: "fa_IR",
    siteName: "فلاح و پسران",
    images: [{ url: "/brand/og-image.png", width: 1200, height: 630, alt: "فلاح و پسران" }],
  },
  twitter: { card: "summary_large_image" },
  manifest: "/manifest.webmanifest",
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#173F35",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fa" dir="rtl" className={`${vazirmatn.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col font-sans">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:start-3 focus:z-[60] focus:rounded-xl focus:bg-green-800 focus:px-4 focus:py-3 focus:text-rice"
        >
          رفتن به محتوای اصلی
        </a>
        <CartProvider>
          <Suspense fallback={<HeaderFallback />}>
            <Header />
          </Suspense>
          <main id="main" className="flex-1">
            {children}
          </main>
          <Suspense fallback={<footer className="mt-20 h-80 bg-green-900" />}>
            <Footer />
          </Suspense>
          <CartToast />
        </CartProvider>
      </body>
    </html>
  );
}
