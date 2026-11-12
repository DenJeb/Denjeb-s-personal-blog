import type { NextConfig } from "next";

const backend = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const proxyPaths = [
  "api",
  "static",
  "admin",
  "login/code",
  "register",
  "forgot-password",
  "reset-password",
  "account",
  "rss.xml",
  "sitemap.xml",
  "robots.txt",
];

const rewrites = proxyPaths.flatMap((path) => [
  { source: `/${path}`, destination: `${backend}/${path}` },
  { source: `/${path}/:path*`, destination: `${backend}/${path}/:path*` },
]);

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    // Use fallback so filesystem routes (including dynamic admin pages such as
    // /admin/moments/[id]/edit) win over the legacy Jinja admin pages; only
    // unmatched paths are proxied to FastAPI.
    return {
      beforeFiles: [],
      afterFiles: [],
      fallback: rewrites,
    };
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "geolocation=(), microphone=(), camera=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
