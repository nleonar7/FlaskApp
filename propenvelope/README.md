# PropEnvelope

NYC property feasibility engine. Enter an address, answer a short AI interview
about what you want to build, and get a zoning feasibility report: how much
buildable envelope remains on the lot and whether your project plausibly fits.

This is a **standalone Next.js app** — a fully encapsulated second product,
separate from the Flask real-estate aggregator it was spun out of. It has no
database and no auth in v1; it fetches lot data live from NYC open data on each
request.

> Screening tool only — **not legal or architectural advice.** Verify every
> figure with a NYC registered architect or expediter.

## How it works

```
address ──▶ NYC GeoSearch ──▶ BBL ──▶ PLUTO (Socrata) ──▶ deterministic
                                                             rules engine
                                                                  │
                    AI interview (Claude) ──▶ intake JSON ────────┼──▶ report
                                                                  │    (Claude
                                        feasibility bundle ───────┘   narrates)
```

Two hard architectural rules (from `SPEC.md`):

1. **All zoning math is deterministic TypeScript** (`lib/zoning/`). The LLM only
   *narrates* numbers the rules engine produced — it never invents them.
2. **Every displayed data point shows its source** PLUTO field, and the app
   **fails loudly** when data is missing rather than guessing.

## Layout

| Path | What |
| --- | --- |
| `lib/pluto.ts` | GeoSearch → BBL → PLUTO fetch, with a fail-loud `PlutoDataError`. |
| `lib/zoning/rules.ts` | District table (R1-2…R5) + envelope/footprint math. |
| `lib/zoning/flags.ts` | Special-case detectors (LDGMA, grandfathering, ADU…). |
| `lib/feasibility.ts` | Bundles PLUTO + rules + flags into the report inputs. |
| `lib/interview.ts` | Claude intake interview → structured summary. |
| `lib/report.ts` | Claude report composer (constrained to the bundle). |
| `app/` | Next.js App Router UI + API routes (`/api/lot`, `/api/interview`, `/api/report`). |
| `tests/` | Vitest unit tests for the rules engine. |
| `scripts/pluto-cli.ts` | CLI smoke test against the live APIs. |

## Setup

```bash
cd propenvelope
npm install
cp .env.example .env.local        # add ANTHROPIC_API_KEY

npm run test                       # rules-engine unit tests (no network/key)
npm run pluto -- "60 Conyingham Ave, Staten Island, NY"   # live PLUTO smoke test
npm run dev                        # http://localhost:3000
```

`ANTHROPIC_API_KEY` is only needed for the interview and report steps; the lot
lookup and rules engine work without it.

## Deploy (Vercel)

1. Push this directory to its own repo (or set it as the Vercel project root).
2. Import into Vercel; set `ANTHROPIC_API_KEY` (and optional `ANTHROPIC_MODEL`,
   `SOCRATA_APP_TOKEN`) as environment variables.
3. Deploy. No database or other services required.

## Status / known gaps

- **Zoning figures are provisional.** FAR values are stable and cross-checked
  against PLUTO's `residfar`; yard/height/coverage values in `rules.ts` are
  marked `verified: false` and must be checked against the current
  [NYC Zoning Resolution](https://zr.planning.nyc.gov/article-ii) before the app
  is presented as authoritative.
- **Model id:** the spec named `claude-sonnet-4-6`; this app defaults to a
  current Claude Sonnet (`ANTHROPIC_MODEL`-overridable) in `lib/anthropic.ts`.
- The report currently renders as preformatted markdown; a markdown renderer is
  a fast-follow.

See `SPEC.md` for full v1 scope and the v2 roadmap (survey/floor-plan CV).
