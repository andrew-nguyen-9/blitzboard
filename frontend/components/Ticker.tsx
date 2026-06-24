// Broadcast lower-third ticker. A "LIVE" tag pinned left; trending items scroll
// past on a seamless CSS marquee (reuses the .marquee keyframe). Canonical tokens.
//
// Accessibility / reduced motion (.ticker rules in globals.css):
//  - the visible duplicate track is aria-hidden so screen readers read each item
//    once; the region is a labelled list.
//  - under prefers-reduced-motion (OS or A11ySettings), the scroll stops and the
//    viewport becomes a horizontally scrollable list — static, nothing clipped.
//  - the marquee pauses on hover/focus-within.
export default function Ticker({
  items,
  duration = 40,
  live = true,
  label = "Trending",
  className = "",
}: {
  items: string[];
  duration?: number;
  live?: boolean;
  label?: string;
  className?: string;
}) {
  const Item = ({ text }: { text: string }) => (
    <span className="flex items-center whitespace-nowrap px-6 py-2 text-label uppercase tracking-[0.18em] text-ink-1">
      <span aria-hidden className="mr-6 inline-block h-1.5 w-1.5 rounded-full bg-accent" />
      {text}
    </span>
  );

  return (
    <div
      className={`ticker flex items-stretch border-y border-line bg-surface ${className}`}
      role="group"
      aria-label={label}
    >
      {live && (
        <span className="ticker__live flex items-center gap-2 border-r border-line bg-ink px-4 text-label font-bold uppercase tracking-[0.2em] text-bg">
          <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-accent" />
          Live
        </span>
      )}
      <div className="ticker__viewport marquee flex-1">
        <ul className="marquee__track" style={{ "--marquee-dur": `${duration}s` } as React.CSSProperties}>
          {items.map((it, i) => (
            <li key={i}>
              <Item text={it} />
            </li>
          ))}
        </ul>
        <ul className="marquee__track" aria-hidden style={{ "--marquee-dur": `${duration}s` } as React.CSSProperties}>
          {items.map((it, i) => (
            <li key={i}>
              <Item text={it} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
