# PropEnvelope — Property Feasibility Engine (MVP Spec)

## One-liner
Enter a NYC address, answer a short AI interview about what you want to build, and get a zoning feasibility report: how much buildable envelope remains on the lot and whether your project (mudroom, ADU, addition, deck, garage conversion) plausibly fits.

## Who it's for
- Homeowners planning additions/renovations (v1 target user)
- Small residential investors evaluating "what can I add to this property?"

## Why now / moat direction
Room-redesign AI apps are saturated. Nobody combines lot-level legal context (zoning, FAR, setbacks, survey) with design intent. v1 skips computer vision entirely by using NYC's structured open data; CV (survey + floor plan parsing) is the v2+ moat.

---

## v1 Scope (build this)

### 1. Address lookup → lot data
- Use NYC Open Data **PLUTO** dataset via the Socrata API (dataset id `64uk-42ks` on data.cityofnewyork.us — verify current id at build time).
- Geocode address → BBL (borough/block/lot). NYC GeoSearch API (https://geosearch.planninglabs.nyc) is free, no key, returns BBL directly.
- Fields needed from PLUTO: `zonedist1`, `lotarea`, `bldgarea`, `builtfar`, `residfar`, `lotfront`, `lotdepth`, `yearbuilt`, `bldgclass`, `landuse`, `borocode`, `block`, `lot`.

### 2. Zoning rules engine (deterministic, no LLM)
- TypeScript module: `zoning/rules.ts` with a table of NYC residential districts (start with R1-2, R2, R3-1, R3-2, R3A, R3X, R4, R4-1, R5 — Staten Island coverage first).
- Per district encode: max FAR, max lot coverage, front/side/rear yard minimums, max building height, parking requirement.
- Compute:
  - `remainingFAR_sqft = max(0, residfar * lotarea - bldgarea)`
  - Buildable footprint estimate from lot dimensions minus required yards (rectangular approximation is fine for v1; state the assumption in output).
- Flag special cases (do NOT try to resolve them, just surface them):
  - Lower Density Growth Management Area (all of Staten Island — affects yards/parking)
  - Pre-existing non-conforming structures (yearbuilt < zoning resolution changes) → "grandfathering review recommended"
  - Attached/semi-detached building classes
  - NYC **Plus One ADU** program eligibility heuristic (1-2 family home, owner-occupied boroughs pilot — link to official page rather than asserting eligibility)

### 3. AI interview (Claude API)
- 5–8 question conversational intake: project type (addition / ADU / garage conversion / deck / interior reconfig), rough desired size, budget band, how they use the home (hosting, hobbies, WFH), style preferences.
- Model: `claude-sonnet-4-6` via Anthropic Messages API. Structured JSON output for the intake summary.

### 4. Feasibility report (LLM-composed from deterministic inputs)
- Inputs to the prompt: PLUTO facts + rules-engine math + interview JSON.
- Output sections: Lot Snapshot, Remaining Envelope, Your Project vs. the Envelope, Flags & Unknowns (encroachments, grandfathering, DOB filing type likely needed: Alt-1/Alt-2), Suggested Next Steps.
- Hard rule in the system prompt: the LLM may not invent zoning numbers; it only narrates numbers provided by the rules engine. Every report ends with a "not legal/architectural advice — verify with a registered architect/expediter" disclaimer.

### 5. UI
- Next.js (App Router) + TypeScript + Tailwind. Single-page flow: address → confirm lot card → chat interview → report page (printable).
- No auth in v1. No payments. Deploy target: Vercel.

---

## Explicitly OUT of v1
- Survey/floor plan upload or parsing (v2)
- Any borough-accurate legal guarantee; this is a screening tool
- Landscaping/interior design generation (v3)
- Non-NYC markets

## v2 (do not build yet, keep architecture friendly to it)
- Survey PDF upload → extract lot dimensions, easements, encroachments (vision model pass, human-confirm step)
- Floor plan upload → room graph extraction → reconfiguration suggestions
- Save/compare multiple properties (investor mode)

---

## Repo structure
```
propenvelope/
  app/                # Next.js app router pages
  lib/pluto.ts        # GeoSearch + PLUTO fetch
  lib/zoning/rules.ts # district table + envelope math
  lib/zoning/flags.ts # special-case detectors
  lib/interview.ts    # Claude interview orchestration
  lib/report.ts       # report generation prompt + call
  tests/              # rules engine unit tests (vitest) — test against 60 Conyingham Ave BBL as fixture
  .env.example        # ANTHROPIC_API_KEY
  SPEC.md             # this file
```

## Build order for Claude Code
1. Scaffold Next.js + TS + Tailwind, commit.
2. `lib/pluto.ts` with GeoSearch→BBL→PLUTO fetch + a CLI test script. Verify against a real Staten Island address. Commit.
3. Rules engine + unit tests (R3-1 first). Commit.
4. Interview flow (API route + simple chat UI). Commit.
5. Report generation + report page. Commit.
6. README with setup + deploy instructions.

## Non-negotiables
- Deterministic math lives in TypeScript, never in the LLM.
- Every external data field displayed to the user shows its source (PLUTO field name).
- Fail loudly if PLUTO data is missing/stale rather than guessing.
