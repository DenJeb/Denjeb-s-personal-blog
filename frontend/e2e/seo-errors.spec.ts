import { expect, test } from "@playwright/test";

test("post page exposes metadata", async ({ page }) => {
  await page.goto("/posts/hello-world");
  await expect(page).toHaveTitle(/Hello World/);

  const canonical = await page
    .locator('link[rel="canonical"]')
    .getAttribute("href");
  expect(canonical).toContain("/posts/hello-world");
});

test("feeds are proxied", async ({ request }) => {
  expect((await request.get("/rss.xml")).headers()["content-type"]).toContain(
    "xml",
  );
  expect((await request.get("/robots.txt")).status()).toBe(200);
});

test("pages expose titles, canonicals and the RSS alternate", async ({
  page,
}) => {
  await page.goto("/posts");
  await expect(page).toHaveTitle(/文章/);
  expect(
    await page.locator('link[rel="canonical"]').getAttribute("href"),
  ).toContain("/posts");
  expect(
    await page
      .locator('link[rel="alternate"][type="application/rss+xml"]')
      .getAttribute("href"),
  ).toContain("/rss.xml");

  await page.goto("/about");
  await expect(page).toHaveTitle(/关于/);
  expect(
    await page.locator('link[rel="canonical"]').getAttribute("href"),
  ).toContain("/about");
});

test("post page exposes Article JSON-LD", async ({ page }) => {
  await page.goto("/posts/hello-world");
  const jsonLd = await page
    .locator('script[type="application/ld+json"]')
    .textContent();
  expect(jsonLd).toContain('"@type":"Article"');
});
