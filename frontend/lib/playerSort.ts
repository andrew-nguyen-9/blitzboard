// Pure, null-safe comparator behind the Players table's dynamic columns (e3):
// any ColDef value is sortable. Kept out of the component so it stays testable
// in the node env (playerSort.test.ts). Box-score → BoxStats reduction lives in
// queries.groupLatestBox (next to its DB fetch).

// Compare two raw column cells. Missing (null) ALWAYS sorts last regardless of
// direction (mirrors the table's prior "missing sorts last"); numbers compare
// numerically, everything else by locale string.
export function compareCells(
  a: number | string | null,
  b: number | string | null,
  asc: boolean,
): number {
  if (a == null) return b == null ? 0 : 1;
  if (b == null) return -1;
  const dir = asc ? 1 : -1;
  if (typeof a === "number" && typeof b === "number") return dir * (a - b);
  return dir * String(a).localeCompare(String(b));
}
