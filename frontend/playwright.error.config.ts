import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: ["**/api-error.spec.ts"],
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3200",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "msedge",
      use: { ...devices["Desktop Chrome"], channel: "msedge" },
    },
  ],
  webServer: [
    {
      command: "node e2e/mock-api/failing-server.mjs",
      port: 8002,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm run dev -- --port 3200",
      port: 3200,
      reuseExistingServer: !process.env.CI,
      env: {
        API_BASE_URL: "http://127.0.0.1:8002",
        NEXT_PUBLIC_SITE_URL: "http://127.0.0.1:3200",
      },
    },
  ],
});
