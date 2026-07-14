// The re-plan gate for the robust strategy tree. An opponent taking a deep bench
// body I never wanted must NOT churn my plan; only a *consequential* pick does.
// Pure predicate so the war room can memoize the plan and re-derive it only when
// this returns true — the "robust strategy tree" contract (inconsequential
// opponent picks don't re-plan).
import { norm } from "@/lib/draftAI";
import type { MappedPick } from "@/lib/sleeperDraft";

export interface ConsequentialCtx {
  mySlot: number;
  needed: Set<string>; // normalized positions still filling one of MY open starter slots
  targetIds: Set<string>; // player ids on my current plan's target/contingency list
  starterCaliberIds: Set<string>; // ids of starter-caliber players (vor>0) at a needed position
}

export interface ConsequentialResult {
  consequential: boolean;
  reason: string;
}

// Is this single pick consequential to MY plan?
export function isConsequential(pick: MappedPick, ctx: ConsequentialCtx): ConsequentialResult {
  if (pick.team === ctx.mySlot) return { consequential: true, reason: "my pick" };
  if (ctx.targetIds.has(pick.player.id)) return { consequential: true, reason: "a planned target was taken" };
  const pos = norm(pick.player.position);
  if (ctx.needed.has(pos) && ctx.starterCaliberIds.has(pick.player.id))
    return { consequential: true, reason: `starter-caliber ${pos} off the board` };
  return { consequential: false, reason: "inconsequential" };
}

// Did anything consequential happen in the picks made since the plan was last built?
// `newPicks` = the slice of picks after the count captured at last plan build.
export function anyConsequential(newPicks: MappedPick[], ctx: ConsequentialCtx): boolean {
  return newPicks.some((p) => isConsequential(p, ctx).consequential);
}
