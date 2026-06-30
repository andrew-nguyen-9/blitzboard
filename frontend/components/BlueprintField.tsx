// Decorative football-play "blueprint" background — hand-drawn route sketches on a
// faint chalk grid, weighted to the right column so it sits behind the hero copy
// without fighting it. Pure static SVG (no Rive, no JS): the routes draw themselves
// in via a CSS stroke-dashoffset loop (.bp-route in globals.css) that collapses to a
// fully-drawn still frame under prefers-reduced-motion / data-motion="reduce".
//
// ponytail: static SVG stands in for the planned Rive scene — .riv authoring needs the
// Rive editor GUI (binary format, not headless-authorable). Swap to <RiveInstrument
// src="/blueprint.riv" fallback={<BlueprintField/>} /> once a scene is authored.
export default function BlueprintField({ className = "" }: { className?: string }) {
  return (
    <svg
      aria-hidden
      className={`bp pointer-events-none ${className}`}
      viewBox="0 0 480 360"
      fill="none"
      preserveAspectRatio="xMaxYMid slice"
    >
      {/* chalk grid */}
      <g className="bp-grid" stroke="currentColor" strokeWidth="0.5">
        {Array.from({ length: 9 }, (_, i) => (
          <line key={`v${i}`} x1={i * 60} y1="0" x2={i * 60} y2="360" />
        ))}
        {Array.from({ length: 7 }, (_, i) => (
          <line key={`h${i}`} x1="0" y1={i * 60} x2="480" y2={i * 60} />
        ))}
      </g>

      {/* line of scrimmage + hash marks */}
      <g className="bp-static" stroke="currentColor" strokeWidth="1.25">
        <line x1="120" y1="210" x2="470" y2="210" strokeWidth="1.75" />
        {Array.from({ length: 8 }, (_, i) => (
          <line key={`hash${i}`} x1={150 + i * 40} y1="204" x2={150 + i * 40} y2="216" />
        ))}
      </g>

      {/* offensive line + QB (O marks), defenders (X marks) */}
      <g className="bp-static" stroke="currentColor" strokeWidth="1.5">
        {[260, 300, 340, 380, 420].map((x) => (
          <circle key={`ol${x}`} cx={x} cy="222" r="6" fill="none" />
        ))}
        <circle cx="340" cy="252" r="6" fill="none" />
        {[270, 330, 390].map((x) => (
          <g key={`d${x}`}>
            <line x1={x - 5} y1="183" x2={x + 5} y2="193" />
            <line x1={x + 5} y1="183" x2={x - 5} y2="193" />
          </g>
        ))}
      </g>

      {/* receiver routes — these draw in (post, out, go, slant) */}
      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path className="bp-route" pathLength={1} d="M250 222 V150 L210 120" />
        <path className="bp-route" pathLength={1} d="M430 222 V160 H470" />
        <path className="bp-route" pathLength={1} d="M395 222 V120" />
        <path className="bp-route" pathLength={1} d="M340 252 L300 200" />
      </g>
    </svg>
  );
}
