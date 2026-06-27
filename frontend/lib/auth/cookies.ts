// Cookie options applied to the Supabase auth session cookies.
// httpOnly => not script-readable; SameSite=Lax so the OAuth redirect-back carries the cookie.
export const AUTH_COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax",
  path: "/",
} as const;
