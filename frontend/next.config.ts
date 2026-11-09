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
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    // Keep these as afterFiles so Next.js admin pages take precedence over
    // the legacy Jinja admin pages served by FastAPI.
    return {
      beforeFiles: [],
      afterFiles: rewrites,
      fallback: [],
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
