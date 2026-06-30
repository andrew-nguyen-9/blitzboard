import type { MetadataRoute } from "next";

// Native App Router robots.txt (no dep). Crawl the public surface; keep crawlers out
// of auth/account flows, the API, and the internal component QA kit. Points at the
// dynamic sitemap (app/sitemap.ts).
const SITE_URL = "https://blitzboard.an9.dev";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/account", "/leagues", "/login", "/signup", "/auth/", "/api/", "/kit"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
