import { asProbability } from "./quantiles";
import type { McProbs } from "./types";

// Monte-Carlo probability badges: bust%, P(top-5), P(beats ADP). Each is omitted
// when the snapshot hasn't published it (null) → the strip never shows a fake 0%.
// Tone is paired with a glyph + explicit label so meaning is never colour-only
// (colourblind-safe, ACCESSIBILITY.md). Static server component.
type Tone = "pos" | "warn" | "neg" | "muted";

const TONE_CLASS: Record<Tone, string> = {
  pos: "border-pos/40 text-pos",
  warn: "border-warn/40 text-warn",
  neg: "border-neg/40 text-neg",
  muted: "border-hairline text-ink-muted",
};

// Band a probability into a tone by threshold; `invert` flips the high band for
// risk metrics (a high bust% is bad, a high upside% is good).
function band(p: number, invert = false): Tone {
  if (p >= 0.5) return invert ? "neg" : "pos";
  if (p >= 0.25) return "warn";
  return "muted";
}

interface Badge {
  key: string;
  label: string;
  glyph: string;
  prob: number;
  tone: Tone;
  tip: string;
}

function pct(p: number): string {
  return `${Math.round(p * 100)}%`;
}

export default function ProbabilityBadges({
  probs,
  className,
}: {
  probs: McProbs | undefined;
  className?: string;
}) {
  const bust = asProbability(probs?.bust);
  const top5 = asProbability(probs?.top5);
  const beatsAdp = asProbability(probs?.beatsAdp);

  const badges: Badge[] = [];
  if (bust != null)
    badges.push({
      key: "bust",
      label: "bust",
      glyph: "▽",
      prob: bust,
      tone: band(bust, true),
      tip: "Probability this player finishes below a replacement-level starter.",
    });
  if (top5 != null)
    badges.push({
      key: "top5",
      label: "top-5",
      glyph: "★",
      prob: top5,
      tone: band(top5),
      tip: "Probability of a positional top-5 finish.",
    });
  if (beatsAdp != null)
    badges.push({
      key: "adp",
      label: "beats ADP",
      glyph: "±",
      prob: beatsAdp,
      tone: band(beatsAdp),
      tip: "Probability this player returns value above its average draft cost.",
    });

  if (badges.length === 0) return null;

  return (
    <ul className={`flex flex-wrap gap-2 ${className ?? ""}`}>
      {badges.map((b) => (
        <li
          key={b.key}
          title={b.tip}
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-label ${TONE_CLASS[b.tone]}`}
          aria-label={`${b.label} probability ${pct(b.prob)}`}
        >
          <span aria-hidden>{b.glyph}</span>
          <span className="uppercase tracking-wide text-ink-2">{b.label}</span>
          <span className="tabular-nums text-ink">{pct(b.prob)}</span>
        </li>
      ))}
    </ul>
  );
}
