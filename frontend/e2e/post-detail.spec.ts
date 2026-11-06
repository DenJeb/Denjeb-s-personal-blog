import { expect, test } from "@playwright/test";

test("renders post detail", async ({ page }) => {
  await page.goto("/posts/hello-world");
  await expect(
    page.getByRole("heading", { name: "Hello World" }),
  ).toBeVisible();
  await expect(page.locator("article img")).toHaveAttribute(
    "src",
    "/static/uploads/test.webp",
  );
});

test("redirects legacy id to slug", async ({ page }) => {
  await page.goto("/posts/42");
  await page.waitForURL("/posts/hello-world");
});

test("styles markdown lists, headings and code", async ({ page }) => {
  await page.goto("/posts/hello-world");

  const listStyle = await page
    .locator(".post-content ul")
    .evaluate((el) => getComputedStyle(el).listStyleType);
  expect(listStyle).toBe("disc");

  const headingSize = await page
    .locator(".post-content h2")
    .evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
  const bodySize = await page
    .locator(".post-content p")
    .first()
    .evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
  expect(headingSize).toBeGreaterThan(bodySize);

  const keywordColor = await page
    .locator(".post-content .k")
    .first()
    .evaluate((el) => getComputedStyle(el).color);
  const bodyColor = await page
    .locator(".post-content p")
    .first()
    .evaluate((el) => getComputedStyle(el).color);
  expect(keywordColor).not.toBe(bodyColor);
});

test("legacy id responds with a permanent redirect", async ({ request }) => {
  const response = await request.get("/posts/42", { maxRedirects: 0 });
  expect(response.status()).toBe(308);
  expect(response.headers()["location"]).toContain("/posts/hello-world");
});

test("unknown slug is 404", async ({ page }) => {
  const response = await page.goto("/posts/missing");
  expect(response?.status()).toBe(404);
  await expect(page.getByText("页面不存在")).toBeVisible();
});
