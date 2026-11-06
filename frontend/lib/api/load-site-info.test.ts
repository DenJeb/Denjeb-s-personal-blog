import { describe, expect, it } from "vitest";

import { siteConfig } from "../site-config";

import { loadSiteInfo } from "./load-site-info";

describe("loadSiteInfo", () => {
  it("falls back to siteConfig when the fetcher fails", async () => {
    const site = await loadSiteInfo(async () => {
      throw new Error("down");
    });

    expect(site.app_name).toBe(siteConfig.name);
    expect(site.author).toBe(siteConfig.author);
  });
});
