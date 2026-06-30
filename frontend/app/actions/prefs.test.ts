import { describe, it, expect, vi, beforeEach } from "vitest";
import { updatePrefs } from "./prefs";

const { getUser, from } = vi.hoisted(() => {
  const eq = vi.fn(async () => ({ error: null }));
  const update = vi.fn(() => ({ eq }));
  const from = vi.fn(() => ({ update }));
  const getUser = vi.fn();
  return { getUser, from };
});

vi.mock("@/lib/supabase/server", () => ({
  getServerSupabase: async () => ({ auth: { getUser }, from }),
}));

describe("updatePrefs", () => {
  beforeEach(() => vi.clearAllMocks());

  it("rejects when unauthenticated", async () => {
    getUser.mockResolvedValue({ data: { user: null } });
    expect(await updatePrefs({ theme: "dark" })).toEqual({ ok: false, error: "unauthenticated" });
  });

  it("validates and writes prefs for an authed user", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u1" } } });
    const res = await updatePrefs({ theme: "dark", reducedMotion: true });
    expect(res).toEqual({ ok: true });
    expect(from).toHaveBeenCalledWith("accounts");
  });

  it("rejects invalid prefs before any write", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u1" } } });
    // legacy/unknown theme values coerce to dark, but a wrong type still fails validation
    await expect(updatePrefs({ reducedMotion: "yes" })).rejects.toThrow();
    expect(from).not.toHaveBeenCalled();
  });
});
