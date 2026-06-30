import { describe, it, expect } from "vitest";
import { gzipSync } from "node:zlib";
import { decodeSnapshot, gunzipJson, type SnapshotPayload } from "./snapshot";

// The publisher (pipeline/publish_snapshot.py) emits a COLUMNAR payload: one array
// per column under `data`, keyed by a short header. These tests pin the client
// decode + the native gzip path the snapshot is delivered with.

const payload: SnapshotPayload = {
  v: 2,
  profile: "default",
  engine: "vorp",
  cols: ["sid", "n", "pos", "tm", "val", "vor", "rnk", "rho", "trend", "adp", "boom", "bust", "bye"],
  count: 2,
  data: [
    ["4046", "6794"],                       // sid
    ["Patrick Mahomes", "Bijan Robinson"],  // n
    ["QB", "RB"],                           // pos
    ["KC", "ATL"],                          // tm
    [120.5, 110.2],                         // val
    [88.3, 70.1],                           // vor
    [1, 2],                                 // rnk
    [0.73, 0.61],                           // rho
    [0, 5],                                 // trend
    [12.1, 8.4],                            // adp
    [140.2, 130.5],                         // boom
    [30.1, 25.6],                           // bust
    [10, 5],                                // bye
  ],
};

describe("decodeSnapshot", () => {
  it("maps columnar data to player objects by column header", () => {
    const players = decodeSnapshot(payload);
    expect(players).toHaveLength(2);
    expect(players[0]).toMatchObject({
      id: "4046", full_name: "Patrick Mahomes", position: "QB",
      nfl_team: "KC", rank: 1, vor: 88.3, predictability: 0.73, trend: 0,
      adp: 12.1, boom: 140.2, bust: 30.1, bye: 10,
    });
    expect(players[1].id).toBe("6794");
    expect(players[1].trend).toBe(5);
  });

  it("null-safe for the adp/boom/bust/bye cols when the snapshot predates them", () => {
    const legacy: SnapshotPayload = {
      ...payload,
      cols: ["sid", "n", "pos", "tm", "val", "vor", "rnk", "rho", "trend"],
      data: payload.data.slice(0, 9),
    };
    const [p] = decodeSnapshot(legacy);
    expect(p.adp).toBeNull();
    expect(p.boom).toBeNull();
    expect(p.bust).toBeNull();
    expect(p.bye).toBeNull();
  });

  it("is resilient to column order (maps by name, not position)", () => {
    const reordered: SnapshotPayload = {
      ...payload,
      cols: ["n", "sid", "rnk", "pos", "tm", "val", "vor", "rho", "trend"],
      data: [
        ["Patrick Mahomes"], ["4046"], [1], ["QB"], ["KC"], [120.5], [88.3], [0.73], [0],
      ],
      count: 1,
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
