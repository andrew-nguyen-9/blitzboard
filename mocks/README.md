# Mocks

Dark "Broadcast Deck" mockups (SVG — open in browser/preview).

| File | What it shows |
|------|---------------|
| [architecture.svg](architecture.svg) | Full system: sources → pipeline → Supabase → 7 frontend tools, + the 4 core abstractions |
| [draft_board_wireframe.svg](draft_board_wireframe.svg) | The centerpiece: live pick ticker, best-available (recomputing), positional scarcity, my roster/needs, trending lower-third, VORP⇄MonteCarlo toggle, ESPN-live→manual fallback |
| [player_card_dataviz.svg](player_card_dataviz.svg) | Instrument readout: radial value gauge, Monte Carlo outcome distribution (floor/μ/ceiling), trending sparkline, sentiment pulse |

These are wireframe intent, not final UI. Final build uses the `creative-dev` skill
(Framer Motion + GSAP/canvas, runtime accent color). See [../docs/DESIGN.md](../docs/DESIGN.md).
