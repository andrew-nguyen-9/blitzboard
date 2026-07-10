import type { Config } from "tailwindcss";

// "Broadcast Deck" theme. All colors are CSS variables (see app/globals.css)
// so dark / light / system swap by flipping `data-theme` on <html> — no
// per-component branching. Accent stays runtime-derived (league color).
const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Canonical OKLCH tokens (source of truth — see app/globals.css).
        accent: "var(--accent)",
        "accent-ink": "var(--accent-ink)",
        "accent-soft": "var(--accent-soft)",
        // Neon North Star (v4 F1) — additive charged-accent layer, data-theme
        // swapped. See docs/design-system/NORTH_STAR.md. Never overrides --accent.
        neon: "var(--neon)",
        "neon-ink": "var(--neon-ink)",
        "neon-dim": "var(--neon-dim)",
        "neon-soft": "var(--neon-soft)",
        bg: "var(--bg-0)",
        surface: "var(--bg-1)",
        "surface-elevated": "var(--bg-2)",
        line: "var(--line)",
        ink: "var(--ink-0)",
        "ink-1": "var(--ink-1)",
        "ink-2": "var(--ink-2)",
        pos: "var(--pos)",
        neg: "var(--neg)",
        warn: "var(--warn)",
        // Legacy aliases (deprecated; map onto the canonical ladder until
        // components migrate in v2.1+).
        hairline: "var(--line)",
        "ink-muted": "var(--ink-2)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        scoreboard: ["var(--font-scoreboard)", "Impact", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        // scoreboard = Anton, condensed athletic → huge ultra-tight numerals
        "score-xl": ["clamp(5rem, 18vw, 16rem)", { lineHeight: "0.82", letterSpacing: "-0.02em", fontWeight: "400" }],
        "display-xl": ["clamp(3.25rem, 9vw, 7rem)", { lineHeight: "0.92", letterSpacing: "-0.035em", fontWeight: "700" }],
        "display-lg": ["clamp(2.5rem, 6vw, 5rem)", { lineHeight: "0.98", letterSpacing: "-0.03em", fontWeight: "700" }],
        "display-md": ["clamp(1.75rem, 3.5vw, 3rem)", { lineHeight: "1.02", letterSpacing: "-0.02em", fontWeight: "600" }],
        heading: ["clamp(1.25rem, 2.2vw, 2rem)", { lineHeight: "1.12", letterSpacing: "-0.01em", fontWeight: "600" }],
        "body-lg": ["1.1875rem", { lineHeight: "1.55", letterSpacing: "-0.01em" }],
        body: ["1rem", { lineHeight: "1.6" }],
        label: ["0.75rem", { lineHeight: "1.2", letterSpacing: "0.14em", fontWeight: "600" }],
      },
      maxWidth: { wide: "1440px" },
      boxShadow: {
        // Neon North Star glow (v4 F1). Multi-layer var — consume via this key so
        // Tailwind emits the raw box-shadow value intact.
        neon: "var(--neon-glow)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: { "fade-up": "fade-up 0.5s ease-out both" },
    },
  },
  plugins: [],
};

export default config;
