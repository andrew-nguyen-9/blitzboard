// Lazy GSAP loader — keeps gsap + ScrollTrigger out of the global bundle. They
// only enter a route's bundle (as an async chunk) when a client component
// actually calls loadGsap(), e.g. the homepage scroll story in v2.1:
//
//   const { gsap, ScrollTrigger } = await loadGsap();
//   gsap.to(el, { x: 100, scrollTrigger: { trigger: el } });
//
// Pair timings with the motion tokens (--dur*, --ease-*) for consistency, and
// gate any ScrollTrigger setup on reduced motion at the call site.
export async function loadGsap() {
  const [{ gsap }, { ScrollTrigger }] = await Promise.all([
    import("gsap"),
    import("gsap/ScrollTrigger"),
  ]);
  gsap.registerPlugin(ScrollTrigger);
  return { gsap, ScrollTrigger };
}
