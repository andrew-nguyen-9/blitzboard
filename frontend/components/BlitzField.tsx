// Decorative "blitz" play behind the hero — a full 22-man formation (11 offense O,
// 11 defense X) on the same chalk grid as BlueprintField, with defenders rushing the
// QB along routes that draw themselves in. Pure static SVG + CSS: the rush paths
// reuse the .bp-route stroke-dashoffset loop (globals.css), so the existing
// prefers-reduced-motion / data-motion="reduce" rules collapse them to a fully-drawn
// still frame for free. aria-hidden — purely ornamental.
//
// Responsive: the secondary (DBs + a safety blitz) is marked .bf-extra and hidden
// under a narrow @media, leaving a recognizable front-seven skeleton that still runs
// the same .bp-route motion on the reduced subset.
//
// Sibling of BlueprintField on purpose — that one is reused by login/e4 and must stay
// intact; this is the homepage hero variant.
export default function BlitzField({ className = "" }: { className?: string }) {
  // O = offense (circles), X = defense (crosses). viewBox is right-weighted (slice)
  // so the core formation sits on the right and stays legible behind the hero copy.
  const ol = [250, 288, 326, 364, 402]; // offensive line
  const dl = [270, 308, 346, 384]; // defensive line
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
        <line x1="120" y1="205" x2="470" y2="205" strokeWidth="1.75" />
        {Array.from({ length: 8 }, (_, i) => (
          <line key={`hash${i}`} x1={150 + i * 40} y1="199" x2={150 + i * 40} y2="211" />
        ))}
      </g>

      {/* OFFENSE (O) — 5 OL, QB, RB, TE, 3 WR = 11 */}
      <g className="bp-static" stroke="currentColor" strokeWidth="1.5">
        {ol.map((x) => (
          <circle key={`ol${x}`} cx={x} cy="220" r="6" />
        ))}
        <circle cx="326" cy="252" r="6" /> {/* QB */}
        <circle cx="288" cy="280" r="6" /> {/* RB */}
        <circle cx="438" cy="220" r="6" /> {/* TE */}
        <circle cx="200" cy="220" r="6" /> {/* WR split end */}
        <circle cx="470" cy="248" r="6" /> {/* WR flanker */}
        <circle cx="164" cy="236" r="6" /> {/* WR slot */}
      </g>

      {/* DEFENSE (X) — 4 DL, 3 LB front seven (always shown) */}
      <g className="bp-static" stroke="currentColor" strokeWidth="1.5">
        {[...dl.map((x) => [x, 190]), [290, 160], [344, 160], [398, 160]].map(([x, y]) => (
          <g key={`d${x}-${y}`}>
            <line x1={x - 5} y1={y - 5} x2={x + 5} y2={y + 5} />
            <line x1={x + 5} y1={y - 5} x2={x - 5} y2={y + 5} />
          </g>
        ))}
      </g>

      {/* DEFENSE secondary (X) — 4 DBs, dropped on small viewports (skeleton) */}
      <g className="bp-static bf-extra" stroke="currentColor" strokeWidth="1.5">
        {[[210, 170], [456, 168], [308, 118], [380, 118]].map(([x, y]) => (
          <g key={`db${x}-${y}`}>
            <line x1={x - 5} y1={y - 5} x2={x + 5} y2={y + 5} />
            <line x1={x + 5} y1={y - 5} x2={x - 5} y2={y + 5} />
          </g>
        ))}
      </g>

      {/* THE BLITZ — defenders rush the QB (326,252); routes draw in via .bp-route.
          The safety blitz is .bf-extra so the mobile skeleton keeps the front rush. */}
      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path className="bp-route" pathLength={1} d="M344 160 L330 246" />
        <path className="bp-route" pathLength={1} d="M384 190 L340 250" />
        <path className="bp-route" pathLength={1} d="M290 160 L322 248" />
        <path className="bp-route" pathLength={1} d="M308 190 L324 244" />
        <path className="bp-route bf-extra" pathLength={1} d="M380 118 L348 248" />
      </g>
    </svg>
  );
}
