// Team logos via the ESPN CDN (no headshots — team logo per player, per spec).
// Sleeper abbreviations mostly match ESPN's; remap the few that differ.
const REMAP: Record<string, string> = {
  WAS: "wsh", // Washington
};

export function teamLogoUrl(abbr: string | null | undefined): string | null {
  if (!abbr) return null;
  const code = (REMAP[abbr] ?? abbr).toLowerCase();
  return `https://a.espncdn.com/i/teamlogos/nfl/500/${code}.png`;
}
