// Tier marker for player rows/cards. Tier is encoded by the NUMERAL (non-colour
// signal); the accent is grouping decoration only, so it reads correctly in every
// colourblind mode. Static — no motion to reduce. Server Component.
export default function TierBadge({
  tier,
  label,
  className,
}: {
  tier: number;
  label?: string;
  className?: string;
}) {
  return (
    <span
      role="img"
      aria-label={`Tier ${tier}${label ? `, ${label}` : ""}`}
      className={`inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-elevated px-2.5 py-1 ${className ?? ""}`}
    >
      {/* accent dot = brand colour as a graphic (not text); the numeral carries
          the tier signal in high-contrast ink so it passes AA at label size. */}
      <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-accent" />
      <span aria-hidden className="font-mono text-label font-semibold tabular-nums text-ink">
        T{tier}
      </span>
      {label && <span aria-hidden className="text-label uppercase text-ink-2">{label}</span>}
    </span>
  );
}
