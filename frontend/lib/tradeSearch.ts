// In-memory player search for the unauth trade calculator (Epic 10). The full
// player universe (~4k) is decoded from the CDN snapshot once, indexed here, then
// searched locally on every keystroke — zero round trips.
//
// A prefix trie keyed on name tokens gives O(len(query)) "starts-with" lookups
// (the common case: you type the first letters of a name). A subsequence pass
// catches typos/middle matches. The trie keeps prefix queries off the linear
// scan; the scan only runs for the fuzzy fallback.
import type { SnapshotPlayer } from "./snapshot";

const normName = (s: string) => s.toLowerCase().replace(/[^a-z0-9 ]/g, " ").trim();

// 26-bit char-presence mask (a–z). Used as a bloom pre-filter before the fuzzy
// subsequence check: if a name is missing any letter the query needs, it cannot
// be a supersequence, so we skip the per-char scan.
// ponytail: N~4k, the fuzzy scan alone already answers in <1ms — this mask is the
// labeled nicety, not a load-bearing index. Drop it if it ever costs more than it
// saves. Upgrade path: a real hashed k-bit bloom only if the universe grows past ~100k.
function charMask(s: string): number {
  let m = 0;
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c >= 97 && c <= 122) m |= 1 << (c - 97);
  }
  return m;
}

function isSubsequence(needle: string, hay: string): boolean {
  let i = 0;
  for (let j = 0; j < hay.length && i < needle.length; j++) {
    if (hay[j] === needle[i]) i++;
  }
  return i === needle.length;
}

interface Node {
  kids: Record<string, Node>;
  end: number[]; // player indices whose token ends here
}

export class PlayerSearchIndex {
  private root: Node = { kids: {}, end: [] };
  private players: SnapshotPlayer[];
  private names: string[]; // normalized, spaces removed (for subsequence)
  private masks: number[];

  constructor(players: SnapshotPlayer[]) {
    this.players = players;
    this.names = new Array(players.length);
    this.masks = new Array(players.length);
    players.forEach((p, i) => {
      const norm = normName(p.full_name);
      this.names[i] = norm.replace(/ /g, "");
      this.masks[i] = charMask(norm);
      for (const tok of norm.split(" ")) if (tok) this.insert(tok, i);
    });
  }

  private insert(tok: string, id: number) {
    let node = this.root;
    for (const ch of tok) node = node.kids[ch] ??= { kids: {}, end: [] };
    node.end.push(id);
  }

  private collect(node: Node, out: Set<number>) {
    for (const id of node.end) out.add(id);
    for (const k in node.kids) this.collect(node.kids[k], out);
  }

  // Player ids whose any name token starts with `tok`.
  private prefix(tok: string): Set<number> {
    let node = this.root;
    for (const ch of tok) {
      const next = node.kids[ch];
      if (!next) return new Set();
      node = next;
    }
    const out = new Set<number>();
    this.collect(node, out);
    return out;
  }

  private rank(i: number): number {
    return this.players[i].rank ?? Number.MAX_SAFE_INTEGER;
  }

  // Ranked best matches for `query`. Prefix matches (every query token starts a
  // name token) come first; a fuzzy subsequence pass fills the rest.
  search(query: string, limit = 12): SnapshotPlayer[] {
    const norm = normName(query);
    if (!norm) return [];
    const tokens = norm.split(" ").filter(Boolean);

    // prefix: intersection — each query token must prefix some name token.
    let prefixIds: Set<number> = this.prefix(tokens[0]);
    for (let i = 1; i < tokens.length && prefixIds.size; i++) {
      const hits = this.prefix(tokens[i]);
      prefixIds = new Set([...prefixIds].filter((id) => hits.has(id)));
    }

    const ordered = [...prefixIds].sort((a, b) => this.rank(a) - this.rank(b));
    if (ordered.length >= limit) return ordered.slice(0, limit).map((i) => this.players[i]);

    // fuzzy fallback: query (spaces removed) is a subsequence of the name.
    const needle = norm.replace(/ /g, "");
    const qMask = charMask(norm);
    const seen = new Set(ordered);
    const fuzzy: number[] = [];
    for (let i = 0; i < this.players.length; i++) {
      if (seen.has(i)) continue;
      if ((this.masks[i] & qMask) !== qMask) continue; // ponytail: bloom pre-filter
      if (isSubsequence(needle, this.names[i])) fuzzy.push(i);
    }
    fuzzy.sort((a, b) => this.rank(a) - this.rank(b));
    return [...ordered, ...fuzzy].slice(0, limit).map((i) => this.players[i]);
  }
}
