"""Base abstractions for listing sources."""

from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

import requests

log = logging.getLogger(__name__)

DEFAULT_UA = (
    'Mozilla/5.0 (FlaskApp listing aggregator; '
    'contact: github.com/nleonar7/FlaskApp)'
)


@dataclass
class ListingDTO:
    """Source-agnostic representation of a single listing."""

    source: str
    source_listing_id: str
    url: str
    title: str

    listing_type: str = 'sale'            # sale | land | rent | auction
    status: str = 'active'                # active | pending | sold | withdrawn

    price_cents: int | None = None

    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    county: str | None = None

    lat: float | None = None
    lng: float | None = None

    lot_sqft: int | None = None
    building_sqft: int | None = None
    acres: float | None = None

    beds: float | None = None
    baths_total: float | None = None
    year_built: int | None = None

    zoning_code: str | None = None
    far_max: float | None = None

    description: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def as_model_kwargs(self) -> dict[str, Any]:
        return asdict(self)


class BaseScraper(ABC):
    """Subclass and set `name` + `supported_regions`, then implement `iter_listings`."""

    name: str = ''
    supported_regions: tuple[str, ...] = ()
    request_delay_seconds: float = 1.0          # polite default
    request_delay_jitter: float = 0.5

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.setdefault('User-Agent', DEFAULT_UA)
        self._last_request_at: float | None = None

    @abstractmethod
    def iter_listings(self, region: str) -> Iterable[ListingDTO]:
        """Yield ListingDTOs for the given region."""
        raise NotImplementedError

    def fetch_detail(self, dto: ListingDTO) -> ListingDTO:
        """Enrich a DTO by fetching its detail page (address, sqft, etc.).

        Default is a no-op; scrapers whose list pages omit fields override
        this. Called by the ingest task for new (and un-enriched) listings.
        Should mutate and return ``dto``; failures should be swallowed so a
        single bad detail page doesn't abort the whole run.
        """
        return dto

    def get(self, url: str, **kwargs) -> requests.Response:
        """Polite GET with per-instance rate limiting."""
        self._sleep_if_needed()
        kwargs.setdefault('timeout', 15)
        resp = self.session.get(url, **kwargs)
        self._last_request_at = time.monotonic()
        log.debug('GET %s -> %s', url, resp.status_code)
        resp.raise_for_status()
        return resp

    def _sleep_if_needed(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        jitter = random.uniform(0, self.request_delay_jitter)
        target = self.request_delay_seconds + jitter
        if elapsed < target:
            time.sleep(target - elapsed)
