// Novice-friendly value framing. Two numbers a beginner can read at a glance:
//   • projPoints — projected fantasy points (vor + replacement). Always positive.
//   • draftScore — a 0–100 grade. 50 ≈ replacement-level (a fine waiver starter),
//     99 ≈ the best player on the board, <50 = bench/depth. No scary negatives.
import type { PlayerWithValue } from "./types";

// A free agent (no NFL team) plays no games, so scores no fantasy points — its
// projected points are 0 regardless of any stale value row. Keeps the board's Pts
// column honest and sinks FAs to the bottom naturally. (Draft-order handling of FAs
// also lives in draftAI's faPenalty; this is the display/points source of truth.)
export const projPoints = (p: PlayerWithValue) =>
  p.nfl_team == null ? 0 : (p.value?.vor ?? 0) + (p.value?.replacement ?? 0);

const shaped = (p: PlayerWithValue) => p.value?.value ?? 0;

// Map shaped draft value → 0..100: positives fill 50→99, negatives fill 50→1.
export function draftScores(players: PlayerWithValue[]): Record<string, number> {
  let maxPos = 1, minNeg = -1;
  for (const p of players) {
    const v = shaped(p);
    if (v > maxPos) maxPos = v;
    if (v < minNeg) minNeg = v;
  }
  const out: Record<string, number> = {};
  for (const p of players) {
    const v = shaped(p);
    const s = v >= 0 ? 50 + 49 * (v / maxPos) : 50 * (1 - v / minNeg);
    out[p.id] = Math.max(1, Math.min(99, Math.round(s)));
  }
  return out;
}

// Color ramp for a 0–100 score (red → amber → accent).
export function scoreColor(s: number): string {
  if (s >= 80) return "var(--accent)";
  if (s >= 60) return "#5AB8FF";
  if (s >= 45) return "#E0A33A";
  return "#8A93A6";
}
