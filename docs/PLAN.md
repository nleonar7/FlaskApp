# Real Estate Aggregation, Filtering & Ranking Platform

## Status (updated 2026-07-07)

| Phase | State | Shipped in |
| --- | --- | --- |
| Phase 0 — Foundations (Flask-Migrate, Celery+Redis, envs, scrape.py cleanup) | ✅ Shipped | `main` |
| Phase 1 — `Listing` model + Craigslist scraper + `/listings` UI | ✅ Shipped (commit `9672b11`) | `main` |
| Phase 2 — Multi-source (Redfin/Realtor), WTForms filter, map endpoint, `SavedSearch` | ⏭ Next | — |
| Phase 3 — Ranking layer (NYC FAR, Upstate land, user-defined) | ⏳ Planned | — |
| Phase 4 — Social layer (comments, digests) | ⏳ Deferred | — |

**Workflow note**: each phase is committed directly to `main` and pushed to `origin/main`. No feature branches or PRs — see `feedback_phase_workflow` memory.

**Exposed secret**: the Google Maps API key `AIzaSyDRB64l8RH...` is in git history (`flaskblog/mapApi.py` prior to Phase 0). Needs rotation in Google Cloud Console — not yet done.

## Context

`FlaskApp` today is a single-module Flask blog with an early prototype `Apartment` model and a brittle, import-time MLS scraper (`flaskblog/scrape.py:4` runs `requests.get` at module load). It already has solid foundations we can reuse: user accounts with admin roles (`flaskblog/models.py:12`), Google Maps integration (`flaskblog/mapApi.py`), Postgres-or-SQLite config, email, and a `/properties` map page.

You want to evolve this into a platform that:
- Continuously ingests sale listings (sale + land) from multiple sources (Realtor.com, Zillow-style, Craigslist, county/MLS scrapes) — **hybrid: scrape first, paid APIs later**
- Covers **NY + neighboring states (NJ, CT, PA, MA, VT)**
- Stores rich, normalized property data so we can filter and rank **at scale**
- Surfaces "valuable" listings via **multiple configurable scorers**: rule-based per region (NYC FAR-driven $/buildable-SF, Upstate $/acre + zoning), comp-delta when sold data is available, and user-defined sorts
- Adds a BringATrailer-style commentary layer in a later phase

The outcome should be: a logged-in user picks a region and criteria, sees the highest-value listings on a map and ranked list, can save searches, and (later) discuss listings with others.

## Architecture Decisions (locked from earlier Q&A)

| Decision | Choice |
| --- | --- |
| Data sources | **Hybrid**: scrape Craigslist/Redfin/Realtor first, paid APIs (ATTOM/Estated/RapidAPI) layered in once value is proven |
| Geographic scope (v1) | NY + NJ + CT + PA + MA + VT, sale + land |
| Background infra | **Celery + Redis** for ingest + scoring; Celery Beat for schedules |
| Ranking | All approaches: rule-based per region (default), user-configurable sort, comp-delta when feasible |

## Phased Delivery

We ship in vertical slices so each phase produces something usable.

### Phase 0 — Foundations (one-time scaffolding)

**Goals**: Make schema changes safe, get Celery/Redis online, fix existing bugs.

1. **Add Flask-Migrate (Alembic)**.
   - Today `db.create_all()` runs in dev (`flaskblog/__init__.py:50`). Fine for the blog schema; will not survive evolving a `Listing` model. Initialize Alembic, baseline current schema, drive all future changes via migrations.
2. **Convert to application factory** (small refactor of `flaskblog/__init__.py`).
   - Required so Celery worker can build its own app context independently of the web process.
3. **Wire Celery + Redis**.
   - New `flaskblog/celery_app.py` exposing a Celery instance bound to Flask app context.
   - New `flaskblog/tasks.py` for task definitions.
   - Redis URL from `REDIS_URL` env var; default to `redis://localhost:6379/0` for dev.
4. **Delete the import-time scraper bug**.
   - `flaskblog/scrape.py:4` issues a network request every time the module is imported. Move that code into a proper scraper class (Phase 1) and remove the module-level call.
5. **Move the hardcoded Google Maps API key** out of `flaskblog/mapApi.py` into `os.environ['GOOGLE_MAPS_API_KEY']`. (Security gap noted in exploration.)
6. **Add PostGIS support** in dev/prod when DB is Postgres (skip on SQLite).
   - Enables fast geo queries (bounding box for map viewport, nearest-neighbor for comps).
   - Add `geoalchemy2` + `shapely` to `requirements.txt`.

**Files touched**: `flaskblog/__init__.py`, `flaskblog/mapApi.py`, `flaskblog/scrape.py` (deleted/moved), `requirements.txt`, new `flaskblog/celery_app.py`, new `flaskblog/tasks.py`, new `migrations/` tree, new `docker-compose.yml` (optional but recommended for local Redis+PostGIS).

### Phase 1 — Listing model + first scraper, end-to-end

**Goals**: Prove the ingest → store → display pipeline with one source, one region.

1. **New `Listing` model** in `flaskblog/models.py` (alongside the existing `Apartment` — we leave `Apartment` untouched for now to avoid breaking `/properties`; we can deprecate later).

   Core columns:
   ```
   id, source (str), source_listing_id (str),  -- unique together
   url, title,
   listing_type (enum: sale | land | rent | auction),
   status (enum: active | pending | sold | withdrawn),
   price (int, cents),
   street, city, state, zip, county,
   lat, lng, geom (PostGIS Point),
   lot_sqft, building_sqft, acres,
   beds, baths_total, year_built,
   zoning_code, far_max,            -- nullable; populated for NYC
   description (text),
   raw_payload (JSONB),             -- source-specific blob for future re-parsing
   first_seen_at, last_seen_at, updated_at
   ```
   Indexes: `(source, source_listing_id)` unique, `(state, price)`, `(state, county)`, GiST on `geom`.

2. **Source-adapter pattern** under new `flaskblog/sources/`:
   - `base.py` — `BaseScraper` ABC with `iter_listings(region) -> Iterable[ListingDTO]` and `name`/`supported_regions` attributes. Rate-limited via shared helper (one polite request/second per host with jitter).
   - `craigslist.py` — first concrete scraper (real estate by owner / land for sale, Binghamton region — the simplest, most permissive source to start with).
   - Reuses existing `requests` + `beautifulsoup4` deps.

3. **Upsert task** in `flaskblog/tasks.py`:
   - `scrape_source(source_name, region)` → fetch DTOs → upsert by `(source, source_listing_id)` → bump `last_seen_at` → set `status=withdrawn` for any listing not seen in N consecutive runs.
   - Celery Beat schedule: every 6h per (source, region).

4. **Geocoding task**: backfill `lat/lng/geom` for any new listing using the existing `googlemaps` dep. Cache results by full address to avoid re-billing.

5. **New `/listings` route** (new blueprint at `flaskblog/listings/routes.py`):
   - GET with basic filters (state, price range, listing_type) → paginated list.
   - Detail page `/listings/<id>`.
   - Existing `/properties` map page stays untouched.

**Files touched**: `flaskblog/models.py`, `flaskblog/tasks.py`, new `flaskblog/sources/`, new `flaskblog/listings/`, new `templates/listings/index.html` + `detail.html`, migrations.

### Phase 2 — Multi-source + map + filters at scale

**Goals**: Ingest from 3+ sources across all 6 states, real filtering UI, map view.

1. **Add scrapers**: `realtor.py` (uses Realtor.com search pages; rotating user agents; cautious rate limits), `redfin.py` (their public search HTML embeds JSON data layer — easier than DOM parsing), `craigslist.py` extended to all NY+neighbor metros. Each registered in a source registry.
2. **Filter form** (`flaskblog/listings/forms.py`) — WTForms with: state(s), county, price range, lot acres range, beds/baths, listing_type, source(s), zoning. URL-encoded so filters are shareable/bookmarkable.
3. **Map endpoint** `/api/listings/geojson` — takes a bbox + filter args, returns GeoJSON FeatureCollection limited to ~500 points; uses PostGIS `ST_MakeEnvelope` + GiST index. Frontend uses Google Maps MarkerClusterer for client-side clustering.
4. **`SavedSearch` model** so logged-in users can persist filter combinations and (later) get email alerts when new matches appear.

**Files touched**: more `flaskblog/sources/*`, `flaskblog/listings/forms.py`, `flaskblog/listings/routes.py`, new `templates/listings/map.html`, migrations.

### Phase 3 — Ranking layer

**Goals**: Ship the "find the best deal" experience.

> **In progress (first slice shipped):** NYC PLUTO valuation foundation. `nyc_pluto_lot`
> (keyed by BBL) + `bbl_cache` models & migration; `flaskblog/pluto/` ingest loader (Socrata
> `64uk-42ks`, no API key); `flaskblog/ranking/pluto.py` metrics (buildable-sqft, FAR-used,
> $/buildable-SF, sqft-discrepancy, free NYC GeoSearch address→BBL); first pluggable scorer
> `UnderbuiltInfillScorer` in `flaskblog/ranking/scorers.py`; and `notebooks/pluto_analysis.ipynb`
> exploratory analysis. Loaded Staten Island + Brooklyn (~402k lots) into local SQLite.
> **Next:** capture listing address/sqft in the scraper to join listings→PLUTO by BBL, then a
> `ListingScore` table + surfacing on `/listings`.

1. **Pluggable scorers** under new `flaskblog/ranking/scorers.py`:
   - `NYCFARScorer` → `price / (lot_sqft * far_max)` = $ per buildable SF. Requires NYC zoning data (we'll ingest the NYC PLUTO open-data dataset as a one-time bulk load into a `nyc_pluto_lot` table keyed by BBL).
   - `UpstateLandScorer` → composite: `price/acre` normalized by county median, bonus for road frontage, penalty for wetlands/floodplain (overlay against FEMA flood layer if loadable).
   - `UserDefinedSortScorer` → just orders by chosen column.
   - `CompDeltaScorer` → deferred until we have a paid API surfacing sold prices.
2. **`ListingScore` table** caches `(listing_id, scorer_name, score, computed_at)`. Recompute task triggered when a listing or scorer changes.
3. **Default sort UI** — user picks scorer; result list shows score breakdown ("$312/buildable SF vs. neighborhood median $480").

**Files touched**: new `flaskblog/ranking/`, model addition for `ListingScore` + `NYCPlutoLot`, route updates to surface scores, new task `recompute_scores`.

### Phase 4 — Social layer (deferred)

`ListingComment` (nested via `parent_id`), upvotes, simple moderation. Patterned after BringATrailer. Email digests of new comments on saved listings.

## Critical Files / Existing Code to Reuse

- `flaskblog/__init__.py:15` — app construction; will become `create_app()` factory
- `flaskblog/models.py:12` — `User` model; reuse as-is (admin flag, email/auth, ratings link)
- `flaskblog/models.py:51` — `Apartment`/`ApartmentScore`; leave intact for the existing `/properties` page, no migration in v1
- `flaskblog/routes.py:24` — `/properties` route; keep; new `/listings` lives in its own blueprint
- `flaskblog/mapApi.py` — Google Maps key wiring; move to env var, then reuse
- `flaskblog/scrape.py` — delete; logic re-homed under `flaskblog/sources/`
- `googlemaps` (already in `requirements.txt:20`) — reuse for geocoding task
- `requirements.txt` — additions: `celery`, `redis`, `flask-migrate`, `geoalchemy2`, `shapely`, `tenacity` (retries), `python-dotenv` (already implied by `__init__.py:11`), `pytest` (uncomment in CI)

## New Dependencies / Infra

- **Redis** — broker + result backend for Celery. Local: docker-compose service. Prod: Heroku Redis addon or managed Redis.
- **PostGIS** — Postgres extension. Local: `postgis/postgis` Docker image. Prod: enable extension in managed Postgres.
- **Celery worker + beat** — two new processes alongside `gunicorn flaskblog:app`. Procfile additions:
  ```
  worker: celery -A flaskblog.celery_app worker --loglevel=info
  beat:   celery -A flaskblog.celery_app beat   --loglevel=info
  ```

## Verification (end-to-end after Phase 1)

1. `docker-compose up` brings up postgres+postgis, redis, web, worker, beat.
2. `flask db upgrade` applies migrations.
3. Manually trigger a scrape:
   `celery -A flaskblog.celery_app call flaskblog.tasks.scrape_source --args='["craigslist","binghamton-ny"]'`
4. Inspect `listing` table — rows present with lat/lng populated by the geocode follow-up task.
5. `GET /listings?state=NY&min_price=10000&max_price=200000` — paginated list renders, filter values round-trip in the URL.
6. `GET /listings/<id>` — detail page shows source link, raw_payload viewable for debugging.
7. Re-run the scrape — `last_seen_at` bumps, no duplicates.
8. Add a unit test for the upsert path (`tests/test_listing_upsert.py`) — currently no test suite exists; this seeds one.

## Open Questions to Decide Together

These are real choices I'd like your input on before we start building:

1. **Phase 0 alone is ~1–2 days of work.** Do you want to do it as a discrete first PR, or fold it into the Phase 1 PR for one bigger jump?
2. **Are we OK adding `docker-compose.yml`** for local dev, or do you prefer to run Postgres+Redis natively?
3. **Migration plan for the existing `Apartment` data** — leave it forever as a separate "blog-era" feature, or eventually port the rows into `listing` and retire `/properties`?
4. **NYC FAR data**: NYC PLUTO is the canonical open dataset (~900k rows, refreshed quarterly). OK to ingest the whole thing into our DB so we can compute FAR for any NYC listing by joining on BBL?
5. **Legal posture**: Realtor.com TOS forbids scraping. The hybrid approach assumes "scrape now, pay later" — are you OK with the operational risk during the scrape phase (IP blocks, possible cease-and-desist if traffic is noticeable)? Craigslist + Redfin + county sites are lower risk.
