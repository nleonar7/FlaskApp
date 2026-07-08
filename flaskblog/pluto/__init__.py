"""NYC PLUTO ingestion.

PLUTO (Primary Land Use Tax Lot Output) is NYC's authoritative tax-lot
dataset. This package streams a chosen subset of it from NYC Open Data into
the local ``nyc_pluto_lot`` table so we can query it by BBL (indexed key
lookups) instead of parsing a giant file at query time.
"""

from flaskblog.pluto.ingest import load_pluto, iter_pluto_rows  # noqa: F401
