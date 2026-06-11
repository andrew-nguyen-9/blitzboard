"use client";

import { useEffect, useState } from "react";

type Pref = "light" | "dark" | "system";
const ORDER: Pref[] = ["system", "light", "dark"];
const LABEL: Record<Pref, string> = { system: "Auto", light: "Light", dark: "Dark" };
const ICON: Record<Pref, string> = { system: "◐", light: "☀", dark: "☾" };

function apply(pref: Pref) {
  const sys = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", pref === "system" ? sys : pref);
  document.documentElement.setAttribute("data-theme-pref", pref);
}

export default function ThemeToggle() {
  const [pref, setPref] = useState<Pref>("system");

  useEffect(() => {
    const saved = (localStorage.getItem("ffdt-theme") as Pref) || "system";
    setPref(saved);
    // keep "system" in sync if the OS theme changes live
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if ((localStorage.getItem("ffdt-theme") || "system") === "system") apply("system");
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  function cycle() {
    const next = ORDER[(ORDER.indexOf(pref) + 1) % ORDER.length];
    setPref(next);
    localStorage.setItem("ffdt-theme", next);
    apply(next);
  }

  return (
    <button
      onClick={cycle}
      aria-label={`Theme: ${LABEL[pref]} (click to change)`}
      title={`Theme: ${LABEL[pref]}`}
      className="flex items-center gap-2 rounded-full border border-hairline bg-surface-elevated px-3 py-1.5 text-label text-ink-muted transition hover:text-ink"
    >
      <span aria-hidden className="text-accent">{ICON[pref]}</span>
      {LABEL[pref]}
    </button>
  );
}
