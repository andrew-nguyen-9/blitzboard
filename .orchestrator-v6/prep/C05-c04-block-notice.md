# C05 — C04 BLOCK notice (2026-08-27)

Append-only. C04 is officially BLOCKED at review commit
`2dd08397869f0fc577af70b68c1fe12b76d2a799` (Andrew's notice).

C05 consequence: nothing changes except the trigger. The branch remains PARKED at accepted-C02
head `417af276`; the checklist in `C05-parked-status.md` now fires on **official C04A PASS +
integration** (not C04). Until then: no adapter recreate, no candidate-SHA freeze, no
`promotion-v3-exec-v1.json`, no authoritative promotion. `promotion-v3.json` remains
byte-for-byte at sha256 `bbb241603a33697bff376b21a2e57e7e066c3c85186eaaab120485ec6bd941ab`.
