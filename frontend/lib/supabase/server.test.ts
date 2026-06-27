import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/headers", () => ({
  cookies: async () => ({ getAll: () => [], set: () => {} }),
}));

describe("getServerSupabase", () => {
  beforeEach(() => {
    vi.resetModules();
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  });

  it("returns null when env is absent (offline-safe)", async () => {
    const { getServerSupabase } = await import("./server");
    expect(await getServerSupabase()).toBeNull();
  });

  it("passes AUTH_COOKIE_OPTIONS to createServerClient when configured", async () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://x.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "anon";
    const createServerClient = vi.fn(() => ({}));
    vi.doMock("@supabase/ssr", () => ({ createServerClient }));
    const { getServerSupabase } = await import("./server");
    await getServerSupabase();
    expect(createServerClient).toHaveBeenCalledWith(
      "https://x.supabase.co",
      "anon",
      expect.objectContaining({
        cookieOptions: expect.objectContaining({ httpOnly: true, sameSite: "lax" }),
      }),
    );
  });
});
