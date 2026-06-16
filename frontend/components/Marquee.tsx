// Broadcast lower-third ticker. Pure CSS marquee (pauses on hover). Duplicates the
// content track so the loop is seamless. Used as a homepage/footer scoreboard strip.
export default function Marquee({
  items,
  duration = 40,
  className = "",
}: {
  items: string[];
  duration?: number;
  className?: string;
}) {
  const Track = () => (
    <div className="marquee__track" style={{ ["--marquee-dur" as any]: `${duration}s` }}>
      {items.map((it, i) => (
        <span key={i} className="flex items-center whitespace-nowrap px-6 py-2 text-label uppercase tracking-[0.18em] text-ink-muted">
          <span className="mr-6 inline-block h-1.5 w-1.5 rounded-full bg-accent" />
          {it}
        </span>
      ))}
    </div>
  );
  return (
    <div className={`marquee border-y border-hairline ${className}`}>
      <Track />
      <Track />
    </div>
  );
}
