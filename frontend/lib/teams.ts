// Team logos via the ESPN team-logo CDN — approved free/licensed-safe source
// (.orchestrator/blockers.md: "Team-logo asset source approved"). Scheme:
//   https://a.espncdn.com/i/teamlogos/nfl/500/<code>.png
// where <code> is the lowercased team abbreviation. CSP img-src + next.config
// remotePatterns already allow a.espncdn.com. Sleeper (our snapshot) abbreviations
// mostly match ESPN's lowercased; remap the ones that differ, incl. legacy codes.
const REMAP: Record<string, string> = {
  WAS: "wsh", // Washington
  OAK: "lv", // legacy Oakland → Las Vegas
  SD: "lac", // legacy San Diego → LA Chargers
  STL: "lar", // legacy St. Louis → LA Rams
  LA: "lar", // ambiguous "LA" → Rams (ESPN's lar)
};

export function teamLogoUrl(abbr: string | null | undefined): string | null {
  if (!abbr) return null;
  const key = abbr.toUpperCase();
  const code = (REMAP[key] ?? abbr).toLowerCase();
  return `https://a.espncdn.com/i/teamlogos/nfl/500/${code}.png`;
}
