"""Load NYC PLUTO tax-lot data into the ``nyc_pluto_lot`` table.

Source: NYC Open Data Socrata dataset ``64uk-42ks`` (no API key required).
We fetch only the boroughs we want via a ``$where`` filter and page through
the JSON API, upserting each row by BBL. Re-running is idempotent — the BBL
primary key means rows overwrite in place.

Typical use (from a notebook or `flask shell`, inside an app context)::

    from flaskblog import app
    from flaskblog.pluto import load_pluto
    with app.app_context():
        load_pluto(('SI', 'BK'))
"""

from __future__ import annotations

import logging
import os
from typing import Iterable

import requests

from flaskblog import db
from flaskblog.models import NycPlutoLot

log = logging.getLogger(__name__)

SOCRATA_URL = 'https://data.cityofnewyork.us/resource/64uk-42ks.json'
PAGE_SIZE = 50000  # Socrata allows large page sizes; ~10 requests for SI+BK.

# Socrata field name -> (model attribute, coercion function).
FIELD_MAP = {
    'borough': ('borough', 'str'),
    'block': ('block', 'int'),
    'lot': ('lot', 'int'),
    'address': ('address', 'str'),
    'zipcode': ('zipcode', 'str'),
    'lotarea': ('lot_area', 'int'),
    'bldgarea': ('bldg_area', 'int'),
    'comarea': ('com_area', 'int'),
    'resarea': ('res_area', 'int'),
    'numfloors': ('num_floors', 'float'),
    'unitsres': ('units_res', 'int'),
    'unitstotal': ('units_total', 'int'),
    'yearbuilt': ('year_built', 'int'),
    'builtfar': ('built_far', 'float'),
    'residfar': ('resid_far', 'float'),
    'commfar': ('comm_far', 'float'),
    'facilfar': ('facil_far', 'float'),
    'landuse': ('land_use', 'str'),
    'zonedist1': ('zone_dist1', 'str'),
    'ownername': ('owner_name', 'str'),
    'assessland': ('assess_land', 'int'),
    'assesstot': ('assess_tot', 'int'),
    'latitude': ('lat', 'float'),
    'longitude': ('lng', 'float'),
    'version': ('pluto_version', 'str'),
}


def load_pluto(
    boroughs: Iterable[str] | None = ('SI', 'BK'),
    *,
    source: str | None = None,
    batch_size: int = 2000,
) -> dict[str, int]:
    """Upsert PLUTO rows for the given boroughs into ``nyc_pluto_lot``.

    ``boroughs`` are two-letter PLUTO codes (MN, BX, BK, QN, SI); None loads
    all five. ``source`` overrides the Socrata endpoint (e.g. a mirror).
    Commits every ``batch_size`` rows. Must run inside a Flask app context.
    """
    processed = 0
    for i, kwargs in enumerate(iter_pluto_rows(source, boroughs), start=1):
        db.session.merge(NycPlutoLot(**kwargs))
        processed += 1
        if i % batch_size == 0:
            db.session.commit()
            log.info('load_pluto: committed %d rows', i)
    db.session.commit()

    total = NycPlutoLot.query.count()
    summary = {'processed': processed, 'table_total': total}
    log.info('load_pluto(%s) -> %s', boroughs, summary)
    return summary


def iter_pluto_rows(
    source: str | None,
    boroughs: Iterable[str] | None,
    *,
    session: requests.Session | None = None,
) -> Iterable[dict]:
    """Page through the Socrata API, yielding normalized model kwargs dicts."""
    url = source or SOCRATA_URL
    sess = session or requests.Session()

    headers = {}
    app_token = os.environ.get('SOCRATA_APP_TOKEN')
    if app_token:
        headers['X-App-Token'] = app_token

    where = None
    if boroughs:
        quoted = ', '.join("'%s'" % b for b in boroughs)
        where = f'borough in ({quoted})'

    offset = 0
    while True:
        params = {
            '$limit': PAGE_SIZE,
            '$offset': offset,
            '$order': ':id',  # stable ordering for deep offset paging
        }
        if where:
            params['$where'] = where

        resp = sess.get(url, params=params, headers=headers, timeout=120)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break

        for raw in rows:
            kwargs = _row_to_kwargs(raw)
            if kwargs:
                yield kwargs

        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE


def _row_to_kwargs(raw: dict) -> dict | None:
    """Map a raw Socrata PLUTO row to ``NycPlutoLot`` kwargs.

    Returns None if the row has no usable BBL (can't be keyed/stored).
    """
    bbl = _normalize_bbl(raw.get('bbl'))
    if not bbl:
        return None

    kwargs: dict = {'bbl': bbl, 'raw_payload': raw}
    for field, (attr, kind) in FIELD_MAP.items():
        value = raw.get(field)
        if kind == 'int':
            kwargs[attr] = _to_int(value)
        elif kind == 'float':
            kwargs[attr] = _to_float(value)
        else:
            kwargs[attr] = _to_str(value)
    return kwargs


def _normalize_bbl(value) -> str | None:
    if value in (None, ''):
        return None
    text = str(value).split('.')[0].strip()  # drop any ".0" from float coercion
    if not text.isdigit():
        return None
    return text.zfill(10)


def _to_int(value) -> int | None:
    if value in (None, ''):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value) -> float | None:
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_str(value) -> str | None:
    if value in (None, ''):
        return None
    return str(value).strip() or None
