import type { MetadataRoute } from "next";

// Web app manifest — product-branded only, no personal identity (D18 / v2.0.5.3).
// theme/background are static hex hints for the install UI (manifests don't take
// OKLCH); they mirror the dark "Broadcast Instrument" page surface.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FFDT — Fantasy Football Draft Tool",
    short_name: "FFDT",
    description:
      "A fantasy football war room: player intelligence, draft assistance, trade & waiver optimization, and news-sentiment trending.",
    start_url: "/",
    display: "standalone",
    background_color: "#0a0b0d",
    theme_color: "#0a0b0d",
  };
}
