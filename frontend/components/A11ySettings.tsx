"use client";

import { useEffect, useState } from "react";

// Accessibility preferences → data-* attributes on <html>, consumed by the
// token CSS in globals.css (no per-component branching). Persisted to
// localStorage; restored pre-paint by ThemeScript so there is no flash.
// Account-synced later in v2.5.
type Scale = "s" | "m" | "l" | "xl";
type Cvd = "none" | "deuteranopia" | "protanopia" | "tritanopia";

const SCALES: { v: Scale; label: string }[] = [
  { v: "s", label: "S" },
  { v: "m", label: "M" },
  { v: "l", label: "L" },
  { v: "xl", label: "XL" },
];
const CVDS: { v: Cvd; label: string }[] = [
  { v: "none", label: "Off" },
  { v: "deuteranopia", label: "Deuteranopia (red-green)" },
  { v: "protanopia", label: "Protanopia (red-green)" },
  { v: "tritanopia", label: "Tritanopia (blue-yellow)" },
];

const K = {
  scale: "ffdt-a11y-type-scale",
  motion: "ffdt-a11y-motion",
  contrast: "ffdt-a11y-contrast",
  cvd: "ffdt-a11y-cvd",
};

const root = () => document.documentElement;
function toggleAttr(name: string, value: string, on: boolean) {
  on ? root().setAttribute(name, value) : root().removeAttribute(name);
}

export default function A11ySettings() {
  const [scale, setScale] = useState<Scale>("m");
  const [motion, setMotion] = useState(false);
  const [contrast, setContrast] = useState(false);
  const [cvd, setCvd] = useState<Cvd>("none");

  // Hydrate control state from storage. The DOM data-* are already applied
  // pre-paint by ThemeScript, so this only syncs the React inputs.
  useEffect(() => {
    setScale((localStorage.getItem(K.scale) as Scale) || "m");
    setMotion(localStorage.getItem(K.motion) === "reduce");
    setContrast(localStorage.getItem(K.contrast) === "high");
    setCvd((localStorage.getItem(K.cvd) as Cvd) || "none");
  }, []);

  function chScale(s: Scale) {
    setScale(s);
    localStorage.setItem(K.scale, s);
    root().setAttribute("data-type-scale", s);
  }
  function chMotion(on: boolean) {
    setMotion(on);
    localStorage.setItem(K.motion, on ? "reduce" : "system");
    toggleAttr("data-motion", "reduce", on);
  }
  function chContrast(on: boolean) {
    setContrast(on);
    localStorage.setItem(K.contrast, on ? "high" : "normal");
    toggleAttr("data-contrast", "high", on);
  }
  function chCvd(c: Cvd) {
    setCvd(c);
    localStorage.setItem(K.cvd, c);
    toggleAttr("data-cvd", c, c !== "none");
  }

  return (
    <details className="a11y group relative">
      <summary
        className="flex h-11 w-11 md:h-9 md:w-9 cursor-pointer list-none items-center justify-center rounded-full text-ink-muted transition hover:bg-surface-elevated hover:text-ink"
        aria-label="Accessibility settings"
        title="Accessibility settings"
      >
        {/* Universal accessibility glyph. Inherits currentColor → theme-adaptive. */}
        <svg viewBox="0 0 24 24" className="h-5 w-5" role="img" aria-hidden focusable="false" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="4" r="1.6" />
          <path d="M4 8h16M12 8v6m0 0l-3.5 6m3.5-6l3.5 6" />
        </svg>
      </summary>
      <div
        role="group"
        aria-label="Accessibility settings"
        className="absolute right-0 z-50 mt-2 w-72 rounded-[var(--radius)] border border-line bg-surface p-4 text-ink shadow-[var(--glow)]"
      >
        <fieldset className="border-0 p-0">
          <legend className="mb-2 text-label text-ink-muted">Text size</legend>
          <div className="flex gap-1" role="radiogroup" aria-label="Text size">
            {SCALES.map((s) => (
              <label
                key={s.v}
                className={`flex min-h-11 flex-1 cursor-pointer items-center justify-center rounded-md border border-line text-center text-label outline-accent focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 ${
                  scale === s.v ? "bg-accent text-accent-ink" : "text-ink-muted hover:text-ink"
                }`}
              >
                <input
                  type="radio"
                  name="a11y-type-scale"
                  className="sr-only"
                  checked={scale === s.v}
                  onChange={() => chScale(s.v)}
                />
                {s.label}
              </label>
            ))}
          </div>
        </fieldset>

        <label className="mt-4 flex min-h-11 items-center justify-between gap-2 text-body">
          Reduce motion
          <input type="checkbox" checked={motion} onChange={(e) => chMotion(e.target.checked)} />
        </label>

        <label className="mt-3 flex min-h-11 items-center justify-between gap-2 text-body">
          High contrast
          <input type="checkbox" checked={contrast} onChange={(e) => chContrast(e.target.checked)} />
        </label>

        <label className="mt-3 flex flex-col gap-1 text-body">
          Color-vision mode
          <select
            value={cvd}
            onChange={(e) => chCvd(e.target.value as Cvd)}
            className="min-h-11 rounded-md border border-line bg-surface-elevated px-2 py-1.5 text-body-lg text-ink"
          >
            {CVDS.map((c) => (
              <option key={c.v} value={c.v}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </details>
  );
}
