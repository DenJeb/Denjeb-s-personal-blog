import { expect, test } from "@playwright/test";

test("healthz checks the API", async ({ request }) => {
  const response = await request.get("/healthz");

  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual({ status: "ok" });
});
