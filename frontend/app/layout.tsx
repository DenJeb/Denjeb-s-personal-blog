import type { Metadata } from "next";
import { Geist_Mono, Manrope } from "next/font/google";
import { cookies } from "next/headers";
import type { ReactNode } from "react";

import { SiteFooter } from "@/components/layout/site-footer";
import { SiteHeader } from "@/components/layout/site-header";
import { siteConfig } from "@/lib/site-config";
import { THEME_COOKIE, type Theme } from "@/lib/theme";

import "./globals.css";
import "./pygments.css";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  ),
  title: {
    default: siteConfig.name,
    template: `%s · ${siteConfig.name}`,
  },
  description: "欢迎来到 Denjeb 的个人博客，这里记录学习、开发与生活。",
  alternates: {
    types: { "application/rss+xml": "/rss.xml" },
  },
  openGraph: {
    type: "website",
    siteName: siteConfig.name,
    title: siteConfig.name,
    description: "欢迎来到 Denjeb 的个人博客，这里记录学习、开发与生活。",
    locale: "zh_CN",
  },
  twitter: {
    card: "summary",
    title: siteConfig.name,
    description: "欢迎来到 Denjeb 的个人博客，这里记录学习、开发与生活。",
  },
};

export default async function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  const theme: Theme =
    (await cookies()).get(THEME_COOKIE)?.value === "light" ? "light" : "dark";

  return (
    <html
      lang="zh-CN"
      data-theme={theme}
      data-scroll-behavior="smooth"
      className={`${manrope.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <SiteHeader />
        <main className="flex-1">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
