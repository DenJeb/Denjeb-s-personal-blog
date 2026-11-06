import { expect, test } from "@playwright/test";

test("sets strict CSP and security headers", async ({ page }) => {
  const response = await page.goto("/");
  const csp = response!.headers()["content-security-policy"];

  expect(csp).toContain("nonce-");
  expect(csp).not.toContain("script-src 'self' 'unsafe-inline'");
  expect(response!.headers()["x-content-type-options"]).toBe("nosniff");
  expect(response!.headers()["x-frame-options"]).toBe("DENY");
});
