import type { NextConfig } from "next";

// In development the storefront proxies backend paths to Django so the browser sees one origin
// (session + CSRF cookies). In production nginx routes these paths to Django directly.
const BACKEND = process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8010";
const PROXIED = ["api/v1", "admin", "bankgateways", "payments", "static", "api/health"];

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
];

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  output: "standalone",
  poweredByHeader: false,
  // Django URLs end with "/"; Next must not 308 them away before the rewrite.
  skipTrailingSlashRedirect: true,
  images: {
    formats: ["image/avif", "image/webp"],
    qualities: [70, 80],
    localPatterns: [
      { pathname: "/media/**", search: "" },
      { pathname: "/brand/**", search: "" },
    ],
  },
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: PROXIED.flatMap((prefix) => [
        { source: `/${prefix}/:path*/`, destination: `${BACKEND}/${prefix}/:path*/` },
        { source: `/${prefix}/:path*`, destination: `${BACKEND}/${prefix}/:path*` },
      ]),
      fallback: [],
    };
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
