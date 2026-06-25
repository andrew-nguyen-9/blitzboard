import { describe, it, expect } from "vitest";
import { gzipSync } from "node:zlib";
import { decodeSnapshot, gunzipJson, type SnapshotPayload } from "./snapshot";

// The publisher (pipeline/publish_snapshot.py) emits a compact array-of-arrays
// payload keyed by a short column header. These tests pin the client decode +
// the native gzip path the snapshot is delivered with.

const payload: SnapshotPayload = {
  v: 1,
  profile: "default",
  engine: "vorp",
  cols: ["sid", "n", "pos", "tm", "val", "vor", "rnk", "boom", "bust", "rho", "trend"],
  count: 2,
  rows: [
    ["4046", "Patrick Mahomes", "QB", "KC", 120.5, 88.3, 1, 140, 30, 0.73, 0],
    ["6794", "Bijan Robinson", "RB", "ATL", 110.2, 70.1, 2, 130, 25, 0.61, 5],
  ],
};

describe("decodeSnapshot", () => {
  it("maps array-of-arrays rows to player objects by column header", () => {
    const players = decodeSnapshot(payload);
    expect(players).toHaveLength(2);
    expect(players[0]).toMatchObject({
      id: "4046", full_name: "Patrick Mahomes", position: "QB",
      nfl_team: "KC", rank: 1, vor: 88.3, predictability: 0.73,
    });
    expect(players[1].id).toBe("6794");
  });

  it("is resilient to column order (maps by name, not position)", () => {
    const reordered: SnapshotPayload = {
      ...payload,
      cols: ["n", "sid", "rnk", "pos", "tm", "val", "vor", "boom", "bust", "rho", "trend"],
      rows: [["Patrick Mahomes", "4046", 1, "QB", "KC", 120.5, 88.3, 140, 30, 0.73, 0]],
    };
    const [p] = decodeSnapshot(reordered);
    expect(p.id).toBe("4046");
    expect(p.full_name).toBe("Patrick Mahomes");
    expect(p.rank).toBe(1);
  });
});

describe("gunzipJson", () => {
  it("decodes gzip-compressed JSON the way the snapshot is delivered", async () => {
    const buf = gzipSync(Buffer.from(JSON.stringify(payload)));
    const out = await gunzipJson(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
    expect(out).toEqual(payload);
  });
});
