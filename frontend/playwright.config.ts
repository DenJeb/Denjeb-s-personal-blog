import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testIgnore: ["**/api-error.spec.ts"],
  reporter: "list",
  // The mock API keeps state in memory and the dev server compiles routes on
  // demand; one worker keeps both deterministic.
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3000",
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
      command: "node e2e/mock-api/server.mjs",
      port: 8001,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm run dev -- --port 3000",
      port: 3000,
      reuseExistingServer: !process.env.CI,
      env: {
        API_BASE_URL: "http://127.0.0.1:8001",
        NEXT_PUBLIC_SITE_URL: "http://127.0.0.1:3000",
      },
    },
  ],
});
