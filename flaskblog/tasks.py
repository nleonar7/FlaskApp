"""Celery task definitions.

Tasks defined here are auto-discovered by `flaskblog.celery_app`.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

from flaskblog import db
from flaskblog.celery_app import celery
from flaskblog.mapApi import map_client
from flaskblog.models import GeocodeCache, Listing
from flaskblog.sources import get_scraper
from flaskblog.sources.base import ListingDTO

log = logging.getLogger(__name__)


@celery.task(name='flaskblog.tasks.ping')
def ping() -> str:
    return 'pong'


@celery.task(name='flaskblog.tasks.scrape_source')
def scrape_source(source_name: str, region: str) -> dict[str, int]:
    """Fetch listings from a source/region and upsert into the DB.

    Returns a small summary dict with counts.
    """
    scraper = get_scraper(source_name)
    now = datetime.utcnow()

    seen_ids: set[str] = set()
    created = updated = 0

    for dto in scraper.iter_listings(region):
        seen_ids.add(dto.source_listing_id)
        existing = Listing.query.filter_by(
            source=dto.source, source_listing_id=dto.source_listing_id
        ).one_or_none()
        if existing is None:
            db.session.add(_dto_to_model(dto, first_seen=now, last_seen=now))
            created += 1
        else:
            _apply_dto(existing, dto, last_seen=now)
            updated += 1

    withdrawn = _mark_withdrawn(source_name, region, seen_ids, now)
    db.session.commit()

    summary = {'created': created, 'updated': updated, 'withdrawn': withdrawn, 'seen': len(seen_ids)}
    log.info('scrape_source(%s,%s) -> %s', source_name, region, summary)
    return summary


@celery.task(name='flaskblog.tasks.geocode_pending')
def geocode_pending(limit: int = 50) -> dict[str, int]:
    """Backfill lat/lng for listings missing geocoordinates."""
    if map_client is None:
        log.info('geocode_pending: GOOGLE_MAPS_API_KEY not set, skipping')
        return {'skipped': 1}

    pending = (
        Listing.query.filter(Listing.lat.is_(None))
        .filter(Listing.city.isnot(None))
        .limit(limit)
        .all()
    )

    hits = misses = cached = 0
    for listing in pending:
        address = _full_address(listing)
        if not address:
            continue
        key = _address_key(address)
        cache = GeocodeCache.query.filter_by(address_key=key).one_or_none()
        if cache and cache.lat is not None:
            listing.lat, listing.lng = cache.lat, cache.lng
            cached += 1
            continue
        try:
            results = map_client.geocode(address)
        except Exception as exc:
            log.warning('geocode failed for %s: %s', address, exc)
            misses += 1
            continue
        if not results:
            db.session.add(GeocodeCache(address_key=key, lat=None, lng=None))
            misses += 1
            continue
        loc = results[0]['geometry']['location']
        listing.lat, listing.lng = loc['lat'], loc['lng']
        db.session.add(GeocodeCache(address_key=key, lat=loc['lat'], lng=loc['lng']))
        hits += 1

    db.session.commit()
    summary = {'hits': hits, 'misses': misses, 'cached': cached, 'pending': len(pending)}
    log.info('geocode_pending -> %s', summary)
    return summary


def _dto_to_model(dto: ListingDTO, *, first_seen: datetime, last_seen: datetime) -> Listing:
    kwargs = dto.as_model_kwargs()
    return Listing(first_seen_at=first_seen, last_seen_at=last_seen, **kwargs)


def _apply_dto(model: Listing, dto: ListingDTO, *, last_seen: datetime) -> None:
    for key, value in dto.as_model_kwargs().items():
        if value is None:
            continue
        if key == 'raw_payload' and not value:
            continue
        setattr(model, key, value)
    model.last_seen_at = last_seen
    if model.status == 'withdrawn':
        model.status = 'active'


def _mark_withdrawn(
    source_name: str, region: str, seen_ids: set[str], now: datetime,
    stale_after: timedelta = timedelta(days=3),
) -> int:
    """Mark any listing from this source/region not seen for `stale_after` as withdrawn."""
    cutoff = now - stale_after
    q = Listing.query.filter(
        Listing.source == source_name,
        Listing.status == 'active',
        Listing.last_seen_at < cutoff,
    )
    if seen_ids:
        q = q.filter(~Listing.source_listing_id.in_(seen_ids))
    count = 0
    for stale in q.all():
        stale.status = 'withdrawn'
        count += 1
    return count


def _full_address(listing: Listing) -> str | None:
    parts: list[str] = []
    for v in (listing.street, listing.city, listing.state, listing.postal_code):
        if v:
            parts.append(v.strip())
    return ', '.join(parts) if parts else None


def _address_key(address: str) -> str:
    normalized = ' '.join(address.lower().split())
    return hashlib.sha1(normalized.encode('utf-8')).hexdigest()
