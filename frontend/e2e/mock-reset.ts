import { test as base } from "@playwright/test";

export const test = base;

// The mock API keeps fixtures in memory. Reset before every spec that mutates
// them so tests are rerunnable and independent of file order.
test.beforeEach(async ({ request }) => {
  const baseURL = process.env.MOCK_API_BASE ?? "http://127.0.0.1:8001";
  await request.post(`${baseURL}/__reset`);
});

export { expect } from "@playwright/test";
