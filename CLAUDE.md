# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Flask blog app evolving into a multi-source real estate listing aggregator + ranker (NY + neighboring states). The roadmap lives in `docs/PLAN.md` — read it before starting phase work and update its status table when a phase ships.

**Workflow**: each phase of work is committed directly to `main` and pushed to `origin/main`. No feature branches or PRs.

## Commands

```bash
python run.py                                  # dev server (debug on unless DYNO is set)
pytest                                         # run tests
pytest tests/test_craigslist_detail.py::test_name   # single test
flake8 flaskblog --count --select=E9,F63,F7,F82 --show-source   # CI lint (errors only)

docker compose up -d                           # local Postgres+PostGIS and Redis (optional; SQLite works)
flask --app flaskblog db upgrade               # apply migrations
flask --app flaskblog db migrate -m "..."      # autogenerate a migration after model changes

celery -A flaskblog.celery_app worker --loglevel=info
celery -A flaskblog.celery_app beat --loglevel=info
# Trigger a scrape manually:
celery -A flaskblog.celery_app call flaskblog.tasks.scrape_source --args='["craigslist","binghamton-ny"]'
```

Config comes from `.env` (loaded unless `FLASK_ENV=production`): `SECRET_KEY`, `SQLALCHEMY_DATABASE_URI` (or `DATABASE_URL` — `postgres://` is auto-rewritten to `postgresql://`), `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` (default `redis://localhost:6379/0`), optional `GOOGLE_MAPS_API_KEY`. Dev DB is SQLite at `instance/posts.db`.

Schema changes go through Flask-Migrate/Alembic migrations — never `db.create_all()`.

**Do not use the paid Google Maps API.** Geocoding via `googlemaps` is legacy/optional (`flaskblog/mapApi.py` degrades to `map_client = None`; `geocode_pending` skips when unset). For NYC address→BBL resolution use the free NYC GeoSearch (`flaskblog/ranking/pluto.py:resolve_bbl`), which caches in `bbl_cache`. Datasets like PLUTO ship their own coordinates.

## Architecture

`flaskblog/` is a single-module Flask app, **not** an app factory: `flaskblog/__init__.py` builds `app`, `db`, `login_manager`, etc. at import time, then imports `routes` and `models` at the bottom (deliberate circular-import pattern — keep new module imports at the bottom too). `flaskblog/celery_app.py` imports that same `app` and wraps every task in an app context, so tasks can use `db`/models directly.

Two generations coexist:

- **Legacy blog era** — `User`, `BlogPost`, `Apartment`/`ApartmentScore` models; all routes in one `flaskblog/routes.py`; `/properties` map page; `flaskblog/scrape.py` (old Binghamton MLS scraper). Left intact; don't extend it.
- **Aggregator era** — everything below. New work goes here.

### Ingest pipeline (scrape → upsert → geocode)

1. **Source adapters** in `flaskblog/sources/`: subclass `BaseScraper` (`base.py`), set `name` + `supported_regions`, implement `iter_listings(region)` yielding `ListingDTO`s, optionally override `fetch_detail(dto)` to enrich from detail pages (address/sqft/coords). Decorate with `@register` and add the module import to `_load_all()` in `sources/__init__.py` — registration happens via import. `BaseScraper.get()` already does polite rate-limiting (1 req/s + jitter); use it for all HTTP.
2. **`scrape_source` task** (`flaskblog/tasks.py`): upserts by the `(source, source_listing_id)` unique key, fetches detail pages for new/un-enriched listings (bounded by `detail_limit`), bumps `last_seen_at`, and marks listings unseen for 3+ days as `withdrawn`. `_apply_dto` skips `None` values so re-scrapes never erase enriched fields.
3. **`geocode_pending` task**: backfills `lat/lng`, caching by address hash in `geocode_cache` (including negative results). No-op without a Maps key.

Money is stored as `price_cents` (BigInteger); `Listing.price_dollars` is the display helper.

### NYC PLUTO valuation layer (Phase 3, in progress)

- `flaskblog/pluto/ingest.py` — bulk-loads NYC's PLUTO tax-lot dataset from Socrata (`64uk-42ks`, no key) into `nyc_pluto_lot`, keyed by 10-char string BBL (leading zeros matter). Idempotent by primary key. Run from `flask shell`/notebook inside an app context.
- `flaskblog/ranking/pluto.py` — pure, null-safe metrics (`buildable_sqft_remaining`, `pct_far_used`) plus `resolve_bbl` (address → BBL via GeoSearch, cached).
- `flaskblog/ranking/scorers.py` — pluggable scorers. Metric math lives in `pluto.py`; scorers own selection policy (which lots qualify) and ranking order. `UnderbuiltInfillScorer` filters out government/institutional/undevelopable parcels before ranking by unused FAR.
- The intended join is listing address → BBL → PLUTO lot; next planned step is a `ListingScore` table surfaced on `/listings`.

### Tests

Tests are deterministic — parsers are exercised against inline HTML fixtures (see `tests/test_craigslist_detail.py`), never the live site. Follow that pattern for new scrapers. CI (`.github/workflows/python-app.yml`) currently runs flake8 only; run `pytest` locally.

## Deploys

- **Procfile** (Heroku-style): gunicorn web + celery worker/beat + `flask db upgrade` on release.
- **PythonAnywhere free-tier demo** (`docs/DEPLOY_PYTHONANYWHERE.md`): no outbound internet and tight disk, so it uses `requirements-web.txt` (slim, no celery/pandas/psycopg2) and a locally-built slim SQLite DB (`python scripts/build_demo_db.py --boroughs SI` drops `raw_payload` and non-selected boroughs). `wsgi_pythonanywhere.py` is the entry point. Ingest always runs locally; the DB file is uploaded.

## Known issues

- A Google Maps API key is exposed in git history (pre-Phase 0 `flaskblog/mapApi.py`) and still needs rotation in Google Cloud Console.
