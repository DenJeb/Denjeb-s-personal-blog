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
    };
  }
}
