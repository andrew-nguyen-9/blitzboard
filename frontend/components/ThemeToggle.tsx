"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

// Default is dark; "light" is the only alternative. Any legacy stored value
// ("system"/"auto") coerces to the dark default.
function readTheme(): Theme {
  const saved = localStorage.getItem("ffdt-theme");
  return saved === "light" ? "light" : "dark";
}

function apply(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.setAttribute("data-theme-pref", theme);
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const t = readTheme();
    setTheme(t);
    // ponytail: migrate any legacy "system"/"auto" preference in place to the
    // dark default so storage and DOM agree. Upgrade path: drop once no clients
    // hold the old value.
    if (localStorage.getItem("ffdt-theme") !== t) localStorage.setItem("ffdt-theme", t);
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("ffdt-theme", next);
    apply(next);
  }

  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";

  return (
    <button
      onClick={toggle}
      aria-label={label}
      title={label}
      className="flex h-9 w-9 items-center justify-center rounded-full text-ink-muted transition hover:bg-surface-elevated hover:text-ink"
    >
      {/* Sun when dark (click → light), moon when light (click → dark). Inherits currentColor. */}
      {theme === "dark" ? (
        <svg viewBox="0 0 24 24" className="h-5 w-5" role="img" aria-hidden focusable="false" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-5 w-5" role="img" aria-hidden focusable="false" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      )}
    </button>
  );
}
