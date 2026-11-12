import { expect, test } from "@playwright/test";

test("sets strict CSP and security headers", async ({ page }) => {
  const response = await page.goto("/");
  const csp = response!.headers()["content-security-policy"];

  expect(csp).toContain("nonce-");
  expect(csp).not.toContain("script-src 'self' 'unsafe-inline'");
  expect(response!.headers()["x-content-type-options"]).toBe("nosniff");
  expect(response!.headers()["x-frame-options"]).toBe("DENY");
});

test("sets CSP on migrated admin pages", async ({ page, context }) => {
  await context.addCookies([
    {
      name: "blog_session",
      value: "admin-session",
      url: "http://127.0.0.1:3000",
    },
  ]);

  const paths = [
    "/admin",
    "/admin/posts",
    "/admin/posts/new",
    "/admin/posts/1/edit",
    "/admin/comments",
    "/admin/moment-comments",
    "/admin/moments",
    "/admin/moments/new",
    "/admin/moments/5/edit",
    "/admin/messages",
    "/admin/users",
    "/admin/uploads",
    "/admin/security",
  ];

  for (const path of paths) {
    const response = await page.goto(path);
    const csp = response!.headers()["content-security-policy"];
    expect(csp, path).toContain("nonce-");
  }
});
