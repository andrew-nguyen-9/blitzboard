import { describe, it, expect } from "vitest";
import { normalize, trigrams, BloomFilter, groupByType, type SearchHit } from "./search";

// Golden Bloom fixture built by pipeline/search_index.py (build_bloom) over the
// trigrams of ["Jalen Hurts","Dallas Cowboys","Patrick Mahomes"]. Hard-coded so
// this test LOCKS cross-language parity: the TS reader must agree with the
// Python writer bit-for-bit (same normalize → trigrams → FNV-1a → packing).
const GOLDEN = {
  m: 328,
  k: 7,
  n: 34,
  bits: "lZ8P7l/n3/50mUVIwrHZ7IdZEDMnAhrOomx6mG3Za5X5MhltsxXzDjE=",
};

describe("normalize", () => {
  it("lowercases and collapses non-alphanumerics to single spaces", () => {
    expect(normalize("  Jalen   HURTS! ")).toBe("jalen hurts");
    expect(normalize("49ers")).toBe("49ers");
    expect(normalize(null)).toBe("");
  });
});

describe("trigrams", () => {
  it("returns 3-char sliding-window substrings", () => {
    expect([...trigrams("jalen")].sort()).toEqual(["ale", "jal", "len"]);
  });
  it("is empty for <3 char input", () => {
    expect(trigrams("jo").size).toBe(0);
  });
});

describe("BloomFilter parity (Python-built fixture)", () => {
  const bf = BloomFilter.fromMeta(GOLDEN);

  it("reads the Python params", () => {
    expect([bf.m, bf.k, bf.n]).toEqual([328, 7, 34]);
  });

  it("NEVER reports a false negative for indexed terms", () => {
    // Every one of these is in the corpus → must survive the pre-check.
    for (const q of ["jalen", "hurts", "dallas", "cowboys", "mahomes", "patrick"]) {
      expect(bf.mightMatch(q)).toBe(true);
    }
  });

  it("short-circuits terms with no trigram overlap", () => {
    expect(bf.mightMatch("zzz")).toBe(false);
  });

  it("passes through queries too short to have trigrams (cannot rule out)", () => {
    expect(bf.mightMatch("jo")).toBe(true);
  });
});

describe("groupByType", () => {
  it("buckets hits by entity type, preserving order", () => {
    const hits: SearchHit[] = [
      { entityType: "player", entityId: "1", label: "A", sublabel: null, url: "/a", score: 1 },
      { entityType: "team", entityId: "DAL", label: "Dallas", sublabel: null, url: "/d", score: 0.9 },
      { entityType: "player", entityId: "2", label: "B", sublabel: null, url: "/b", score: 0.8 },
    ];
    const g = groupByType(hits);
    expect(g.player.map((h) => h.entityId)).toEqual(["1", "2"]);
    expect(g.team.map((h) => h.entityId)).toEqual(["DAL"]);
    expect(g.news).toEqual([]);
  });
});
