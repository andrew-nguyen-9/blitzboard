// Radial value gauge (instrument readout, per the player-card mock).
// `fraction` (0..1) fills the arc; the big number is whatever you pass (rank/VOR).
export default function ValueDial({
  fraction,
  label,
  value,
  sub,
}: {
  fraction: number;
  label: string;
  value: string;
  sub?: string;
}) {
  const f = Math.max(0, Math.min(1, fraction));
  const r = 84;
  const c = 2 * Math.PI * r;
  // 270° arc (gap at the bottom), starting from lower-left
  const arc = 0.75;
  const dash = `${c * arc * f} ${c}`;
  return (
    <div className="relative grid place-items-center" style={{ width: 220, height: 220 }}>
      <svg width="220" height="220" viewBox="0 0 220 220" className="-rotate-[135deg]">
        <circle cx="110" cy="110" r={r} fill="none" stroke="var(--hairline)" strokeWidth="14"
          strokeDasharray={`${c * arc} ${c}`} strokeLinecap="round" />
        <circle cx="110" cy="110" r={r} fill="none" stroke="var(--accent)" strokeWidth="14"
          strokeDasharray={dash} strokeLinecap="round" />
      </svg>
      <div className="absolute text-center">
        <div className="font-mono text-display-md leading-none">{value}</div>
        <div className="mt-1 text-label text-ink-muted">{label}</div>
        {sub && <div className="mt-0.5 text-label text-accent">{sub}</div>}
      </div>
    </div>
  );
}
