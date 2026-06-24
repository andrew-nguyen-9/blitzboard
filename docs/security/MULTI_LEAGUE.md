# Multi-League Accounts + League-Rules Import

> Requirements: a user can connect their Sleeper/ESPN league; import their league's **rules**
> for a tailored experience; and hold **multiple leagues** within their authenticated space.
> Phase **v2.5** (data model + import), surfaced in **v2.6** (gated tabs).

## Data model (per-user, RLS-isolated)

```
accounts            (1:1 auth.users)
  user_id PK/FK → auth.users
  display_name, email, created_at, prefs (a11y/theme JSONB)

user_leagues        (N per account)
  id PK, user_id FK
  platform ('espn' | 'sleeper' | 'manual')
  external_league_id, season
  name, scoring_profile_id FK → league_rules
  is_default bool
  RLS: user_id = auth.uid()

league_rules        (the v1 LeagueRules shape, now multi-tenant)
  id PK, owner_user_id FK (null = public/global preset)
  config JSONB  -- scoring weights, roster slots, superflex flag, distance-K, yardage-D/ST,
                --  waiver type (FAAB), league size, etc. (same shape as Smores 2025 seed)

credential_vault    (encrypted; see SECURITY.md)
  user_id FK, platform, ciphertext, masked_hint, status, expires_at
  RLS: user_id = auth.uid()
```

`league_rules` is the v1 `LeagueRules` JSONB generalized: it already encodes superflex/OP
eligibility, distance-based K, yardage D/ST, FAAB — so any league's settings populate the same
shape, and the `ValueEngine` derives replacement levels from *that league's* slot demand.

## League-rules import

- **Sleeper**: public API → pull `league` settings (scoring, roster positions, waiver type,
  size) → map into the `league_rules` JSONB. No credentials needed for public leagues.
- **ESPN**: with the user's vaulted `espn_s2`/`SWID` → `league_sync.py` pulls settings →
  same mapping. The crosswalk (ESPN id → Sleeper id → our id) from v1 P5 is reused.
- **Validation + review**: after import, show the parsed rules for the user to confirm/edit
  (scoring, slots, superflex detection) before it drives value — never silently mis-score.
- **Manual**: a guided rules editor for leagues we can't auto-pull (or to override).

## Tailored experience

Once a league's rules are imported and set active:
- All value (VORP/MC) is computed against *that* `scoring_profile` (the pipeline precomputes
  per profile; the snapshot layer is keyed by profile — `DATA_TRANSFER.md`).
- Draft policy, waiver bids (FAAB-aware), trade fairness all read the active league's rules.
- A league switcher lets the user flip between their leagues; `is_default` picks the landing one.

## Scaling note

The pipeline precomputes value per **distinct scoring profile**, not per user — many users
share common profiles (standard, half-PPR, superflex, etc.), so the snapshot set stays small.
Truly bespoke profiles compute on a schedule / on first connect. This keeps multi-league
cheap without per-user live computation.

## Acceptance (v2.5)

- A user can connect ≥1 ESPN and ≥1 Sleeper league, import rules, confirm them, and switch
  between leagues — all RLS-isolated.
- Imported rules correctly detect superflex, distance-K, yardage-D/ST, FAAB.
- Value shown in gated tabs reflects the active league's rules.
