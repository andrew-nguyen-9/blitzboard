import type { MetadataRoute } from "next";
import { getSitemapPlayerIds } from "@/lib/queries";

// Native App Router sitemap (no dep). Lists the public, indexable surface only —
// the auth/utility routes (/account, /leagues, /login, /signup, /auth/*, /api/*, /kit)
// are excluded here and Disallowed in app/robots.ts. Player detail pages are
// enumerated from the DB; with no keys the query returns [] and we emit just the
// static routes (ships with no backend, per the project's empty-state rule).
const SITE_URL = "https://blitzboard.an9.dev";

// [path, changeFrequency, priority] — the static public marketing/tool surface.
const STATIC_ROUTES: [string, MetadataRoute.Sitemap[number]["changeFrequency"], number][] = [
  ["/", "daily", 1],
  ["/players", "daily", 0.9],
  ["/draft", "weekly", 0.8],
  ["/trades", "weekly", 0.7],
  ["/waivers", "daily", 0.7],
  ["/league", "weekly", 0.6],
  ["/about", "monthly", 0.4],
  ["/privacy", "yearly", 0.2],
  ["/terms", "yearly", 0.2],
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const lastModified = new Date();
  const ids = await getSitemapPlayerIds();

  return [
    ...STATIC_ROUTES.map(([path, changeFrequency, priority]) => ({
      url: `${SITE_URL}${path}`,
      lastModified,
      changeFrequency,
      priority,
    })),
    ...ids.map((id) => ({
      url: `${SITE_URL}/players/${id}`,
      lastModified,
      changeFrequency: "weekly" as const,
      priority: 0.5,
    })),
  ];
}
