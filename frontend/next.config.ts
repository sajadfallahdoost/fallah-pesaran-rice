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

const revision = process.env.RELEASE_REVISION;
if (revision && !/^[a-f0-9]{40}$/.test(revision)) {
  throw new Error("RELEASE_REVISION must be a full Git SHA");
}

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  output: "standalone",
  poweredByHeader: false,
  // Resolve existence and canonical metadata before committing the HTTP response.
  htmlLimitedBots: /.*/,
  ...(revision ? { generateBuildId: async () => revision } : {}),
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
  async redirects() {
    // CMS also has an "about" page; the public URL is /about to avoid duplicate content.
    return [
      { source: "/info/about", destination: "/about", permanent: true },
      { source: "/info/about/", destination: "/about", permanent: true },
      { source: "/:section(shop|guides|about|contact|faq)/", destination: "/:section", permanent: true },
      {
        source: "/:section(product|category|guides|info)/:slug/",
        destination: "/:section/:slug",
        permanent: true,
      },
    ];
  },
  async headers() {
    const releaseHeaders = revision ? [{ key: "X-Fallah-Release", value: revision }] : [];
    return [{ source: "/:path*", headers: [...securityHeaders, ...releaseHeaders] }];
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
