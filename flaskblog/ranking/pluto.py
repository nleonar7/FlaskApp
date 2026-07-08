"""PLUTO-based valuation metrics.

Pure, null-safe helpers plus one cached network call (``resolve_bbl``). The
metrics that power the initial under-built analysis (``buildable_sqft_remaining``,
``pct_far_used``) run entirely off the stored ``nyc_pluto_lot`` table — no
network, no listings.

``resolve_bbl`` uses NYC Planning's **free** GeoSearch service (no Google Maps
billing) and caches results in ``BblCache``.
"""

from __future__ import annotations

import hashlib
import logging

import requests

from flaskblog import db
from flaskblog.models import BblCache, NycPlutoLot

log = logging.getLogger(__name__)

GEOSEARCH_URL = 'https://geosearch.planninglabs.nyc/v2/search'


def resolve_bbl(address: str, *, min_confidence: float = 0.7) -> str | None:
    """Resolve a street address to a BBL via NYC GeoSearch, cached in BblCache.

    Returns a 10-char BBL string, or None if nothing clears ``min_confidence``.
    A negative result (no match) is cached too, so we never re-query it.
    Must run inside a Flask app context.
    """
    if not address or not address.strip():
        return None

    key = _address_key(address)
    cache = BblCache.query.filter_by(address_key=key).one_or_none()
    if cache is not None:
        if cache.bbl and (cache.confidence or 0) >= min_confidence:
            return cache.bbl
        return None

    bbl, confidence = _geosearch(address)
    db.session.add(BblCache(address_key=key, bbl=bbl, confidence=confidence))
    db.session.commit()

    if bbl and (confidence or 0) >= min_confidence:
        return bbl
    return None


def get_pluto(bbl: str) -> NycPlutoLot | None:
    """Primary-key lookup of a stored lot (indexed, sub-millisecond)."""
    normalized = _normalize_bbl(bbl)
    if not normalized:
        return None
    return db.session.get(NycPlutoLot, normalized)


def buildable_sqft_remaining(lot: NycPlutoLot) -> float | None:
    """Unused developable floor area: ``max_far * lot_area - bldg_area``,
    floored at 0. None if the inputs needed aren't present."""
    max_far = lot.max_far
    if max_far is None or lot.lot_area is None:
        return None
    built = lot.bldg_area or 0
    return max(0.0, max_far * lot.lot_area - built)


def pct_far_used(lot: NycPlutoLot) -> float | None:
    """Fraction of allowable FAR already built (``built_far / max_far``).

    Values near 0 mean heavily under-built (air-rights upside); >1 means
    over-built (e.g. grandfathered). None if FAR data is missing."""
    max_far = lot.max_far
    if max_far is None or max_far == 0 or lot.built_far is None:
        return None
    return lot.built_far / max_far


def price_per_buildable_sf(price_cents: int, lot: NycPlutoLot) -> float | None:
    """The relative-value metric: dollars per remaining buildable square foot.
    None if there's no price or no remaining buildable area."""
    if price_cents is None:
        return None
    remaining = buildable_sqft_remaining(lot)
    if not remaining:  # None or 0
        return None
    return (price_cents / 100.0) / remaining


def sqft_discrepancy(reported_sqft: int, lot: NycPlutoLot, *, tolerance: float = 0.10) -> dict | None:
    """Compare a listing's reported building sqft to PLUTO's ``bldg_area``.

    Returns a dict describing the gap, or None if inputs are missing::

        {'reported', 'record', 'delta', 'pct_diff', 'flag'}

    ``flag`` is 'over' (listing claims more than the record), 'under', or
    'match' (within ``tolerance``). Used by the next slice to surface
    listings whose advertised size disagrees with the official record.
    """
    if reported_sqft is None or lot.bldg_area is None or lot.bldg_area == 0:
        return None
    record = lot.bldg_area
    delta = reported_sqft - record
    pct_diff = delta / record
    if abs(pct_diff) <= tolerance:
        flag = 'match'
    elif delta > 0:
        flag = 'over'
    else:
        flag = 'under'
    return {
        'reported': reported_sqft,
        'record': record,
        'delta': delta,
        'pct_diff': pct_diff,
        'flag': flag,
    }


# --- internals -------------------------------------------------------------

def _geosearch(address: str) -> tuple[str | None, float | None]:
    """Query NYC GeoSearch; return (bbl, confidence) of the top result."""
    try:
        resp = requests.get(GEOSEARCH_URL, params={'text': address}, timeout=15)
        resp.raise_for_status()
        features = resp.json().get('features') or []
    except Exception as exc:  # network / parse failure -> treat as no match
        log.warning('GeoSearch failed for %r: %s', address, exc)
        return None, None
    if not features:
        return None, None
    props = features[0].get('properties', {})
    bbl = (((props.get('addendum') or {}).get('pad') or {}).get('bbl'))
    confidence = props.get('confidence')
    return (_normalize_bbl(bbl), confidence)


def _normalize_bbl(value) -> str | None:
    if value in (None, ''):
        return None
    text = str(value).split('.')[0].strip()
    if not text.isdigit():
        return None
    return text.zfill(10)


def _address_key(address: str) -> str:
    normalized = ' '.join(address.lower().split())
    return hashlib.sha1(normalized.encode('utf-8')).hexdigest()
