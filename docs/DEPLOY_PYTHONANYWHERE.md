# Deploying the demo to PythonAnywhere (free tier, no credit card)

This gets the Flask site running at `https://<username>.pythonanywhere.com` so you
can click around `/listings` and the aggregated data. It is a **demo** deploy:
the background stack (Celery/Redis) and live ingest don't run here.

## Two free-tier constraints that shape everything

1. **No arbitrary outbound internet.** Free accounts can only reach a proxy
   allowlist (github is allowed; `data.cityofnewyork.us` and craigslist are
   not). So the server **cannot** run the PLUTO loader or the scrapers — we
   build the data locally and **upload the SQLite file**.
2. **512 MB disk + 100 MB per web upload.** The full DB is ~820 MB (mostly the
   PLUTO `raw_payload` blob), and the full `requirements.txt` (pandas, jupyter,
   celery, shapely…) is huge. We use a **slim DB** and a **slim requirements
   file** (`requirements-web.txt`) instead.

---

## Step 0 — build the slim demo DB (local machine)

```bash
# Staten Island only → ~34 MB, safely under the 100 MB upload cap.
python scripts/build_demo_db.py --dest demo_posts.db --boroughs SI
```

This copies `instance/posts.db`, drops `raw_payload`, keeps SI, and VACUUMs.
(Omit `--boroughs SI` for all boroughs, but that's ~107 MB — too big for the
web-upload cap; you'd need SI-only for the free tier.) The DB already contains
the schema + PLUTO rows + any scraped listings, so **no migrations are needed
on the server**.

## Step 1 — create the account

Sign up for a free **"Beginner"** account at pythonanywhere.com (no card).

## Step 2 — get the code (Bash console on PythonAnywhere)

```bash
git clone https://github.com/nleonar7/FlaskApp.git
```

## Step 3 — virtualenv + slim deps

```bash
mkvirtualenv --python=python3.10 flaskapp        # note the venv path it prints
pip install -r FlaskApp/requirements-web.txt
```

## Step 4 — upload the DB

On the **Files** tab, into `/home/<username>/FlaskApp/instance/` (create the
`instance` folder if needed), upload `demo_posts.db` and name it **`posts.db`**.
Final path: `/home/<username>/FlaskApp/instance/posts.db`.

## Step 5 — create the web app

On the **Web** tab → **Add a new web app** → **Manual configuration** →
**Python 3.10**. Then set:

- **Source code:** `/home/<username>/FlaskApp`
- **Virtualenv:** `/home/<username>/.virtualenvs/flaskapp`
- **WSGI configuration file:** click it, delete the template, and paste the
  contents of `wsgi_pythonanywhere.py` from this repo. Edit the three CHANGE-ME
  values (your username in two paths, and a random `SECRET_KEY`).

## Step 6 — reload & visit

Hit the green **Reload** button, then open:

- `https://<username>.pythonanywhere.com/` — home
- `https://<username>.pythonanywhere.com/listings` — the aggregator (filters, detail pages)

---

## Refreshing the data later

Because the server can't fetch data, re-run the loaders/scrapers **locally**
(`load_pluto(...)`, `scrape_source(...)`), rebuild the slim DB with
`scripts/build_demo_db.py`, re-upload it as `posts.db`, and **Reload** the web
app.

## Notes

- Free web apps must be renewed every ~3 months (a button on the Web tab).
- `GOOGLE_MAPS_API_KEY` is intentionally left unset — the site needs no paid
  Maps calls; PLUTO ships its own coordinates.
- The PLUTO valuation ranking currently lives in `notebooks/pluto_analysis.ipynb`
  (run locally), not a web page yet — a `/valuation` route is a natural next step
  if you want it visible on the hosted site.
