import type { Metadata } from "next";
import { Bricolage_Grotesque, Anton, Hanken_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";
import ThemeScript from "@/components/ThemeScript";
import Cursor from "@/components/Cursor";
import SmoothScroll from "@/components/SmoothScroll";

// Self-hosted at build time via next/font (no render-blocking <link>, no layout
// shift, clears @next/next/no-page-custom-font). Each exposes a CSS variable the
// token layer consumes (globals.css: --font-display/-scoreboard/-sans/-mono).
// Only the two above-the-fold faces — Bricolage (hero headline) and Hanken
// (body) — are preloaded; Anton (scoreboard) and JetBrains (mono numerals)
// appear lower on the page, so preloading them would queue ahead of and delay
// the LCP text font on slow connections. They still load on demand (swap).
const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-bricolage", display: "swap" });
const scoreboard = Anton({ subsets: ["latin"], weight: "400", variable: "--font-anton", display: "swap", preload: false });
const body = Hanken_Grotesk({ subsets: ["latin"], variable: "--font-hanken", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains", display: "swap", preload: false });

const fontVars = `${display.variable} ${scoreboard.variable} ${body.variable} ${mono.variable}`;

export const metadata: Metadata = {
  title: {
    default: "FFDT — Fantasy Football Draft Tool",
    template: "%s · FFDT",
  },
  description:
    "A fantasy football war room: player intelligence, draft assistance (live + offline), trade & waiver optimization, and real-time news-sentiment trending.",
  metadataBase: new URL("https://ffdt.vercel.app"),
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={fontVars} suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className="min-h-screen font-sans antialiased">
        <a href="#main" className="skip-link">Skip to content</a>
        <div className="grain-overlay" aria-hidden />
        <SmoothScroll />
        <Cursor />
        <Nav />
        <main id="main" className="mx-auto max-w-wide px-5 md:px-8">{children}</main>
        <footer className="mx-auto mt-24 max-w-wide border-t border-line px-5 py-10 text-label text-ink-2 md:px-8">
          FFDT · Data from Sleeper, nflverse &amp; ESPN · Built with Next.js + Supabase
        </footer>
      </body>
    </html>
  );
}
