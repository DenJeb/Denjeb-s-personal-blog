import { siteConfig } from "../site-config";

import type { SiteInfo } from "./fetchers";

export async function loadSiteInfo(
  fetcher: () => Promise<SiteInfo>,
): Promise<SiteInfo> {
  try {
    return await fetcher();
  } catch {
    return {
      app_name: siteConfig.name,
      author: siteConfig.author,
      site_url: siteConfig.url,
      // Only used to keep the shell rendering while the API is down; pages
      // that need the site-timezone date fetch /api/v1/site directly.
      today: new Date().toISOString().slice(0, 10),
    };
  }
}
