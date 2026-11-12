import { NextResponse, type NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const isDev = process.env.NODE_ENV === "development";

  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  // FastAPI/Jinja2 页面（旧后台、验证码登录、注册/找回、/account/delete）和
  // API/静态资源由 Nginx 直接路由；开发环境也排除它们，避免 Next 的 CSP
  // 叠加到 FastAPI 页面。已迁移到 Next.js 的页面单独加入，使用 nonce CSP。
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|api/|static/|admin|login/code|register|forgot-password|reset-password|account|rss\\.xml|sitemap\\.xml|robots\\.txt).*)",
    "/admin",
    "/admin/posts",
    "/admin/posts/new",
    "/admin/posts/:id/edit",
    "/admin/comments",
    "/admin/moment-comments",
    "/admin/moments",
    "/admin/moments/new",
    "/admin/moments/:id/edit",
    "/admin/messages",
    "/admin/users",
    "/admin/uploads",
    "/admin/security",
    "/account",
  ],
};
