import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import ThemeScript from "@/components/ThemeScript";
import Cursor from "@/components/Cursor";
import SmoothScroll from "@/components/SmoothScroll";

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
    <html lang="en" suppressHydrationWarning>
      <head>
        <ThemeScript />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300..800&family=Anton&family=Hanken+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap"
        />
      </head>
      <body className="min-h-screen font-sans antialiased">
        <a href="#main" className="skip-link">Skip to content</a>
        <div className="grain-overlay" aria-hidden />
        <SmoothScroll />
        <Cursor />
        <Nav />
        <main id="main" className="mx-auto max-w-wide px-5 md:px-8">{children}</main>
        <footer className="mx-auto mt-24 max-w-wide border-t border-hairline px-5 py-10 text-label text-ink-muted md:px-8">
          FFDT · Data from Sleeper, nflverse &amp; ESPN · Built with Next.js + Supabase
        </footer>
      </body>
    </html>
  );
}
