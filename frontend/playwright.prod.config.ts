import { defineConfig, devices } from "@playwright/test";

process.env.MOCK_API_BASE = "http://127.0.0.1:8000";

const useEdge = !process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  testIgnore: ["**/api-error.spec.ts"],
  reporter: "list",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: useEdge ? "msedge" : "chromium",
      use: useEdge
        ? { ...devices["Desktop Chrome"], channel: "msedge" }
        : { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      // Rewrites are baked into the production build, so the mock must use
      // the same port as the build-time API_BASE_URL (8000 by default).
      command: "node e2e/mock-api/server.mjs",
      port: 8000,
      reuseExistingServer: !process.env.CI,
      env: { MOCK_API_PORT: "8000" },
    },
    {
      command: "npm run start -- --port 3100",
      port: 3100,
      reuseExistingServer: !process.env.CI,
      env: {
        API_BASE_URL: "http://127.0.0.1:8000",
        NEXT_PUBLIC_SITE_URL: "http://127.0.0.1:3100",
      },
    },
  ],
});
