"""Craigslist real-estate-for-sale scraper.

Parses Craigslist's static search results HTML at
    https://{region}.craigslist.org/search/{section}

Sections used:
    rea - real estate for sale (houses, condos, land)
    rfs - real estate by owner
    lnd - land for sale (some regions)

Regions are the Craigslist subdomain prefix (e.g. "binghamton", "newyork",
"longisland", "albany"). The static search HTML lists posts as
`<li class="cl-static-search-result">` elements containing the title,
price, and post URL — robust enough to parse without JS rendering.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from flaskblog.sources import register
from flaskblog.sources.base import BaseScraper, ListingDTO

log = logging.getLogger(__name__)

SECTION = 'rea'

# Region subdomain -> (default state, county hint).
# Hints are best-effort and get used when the listing itself doesn't carry one.
REGION_HINTS = {
    'binghamton': ('NY', 'Broome'),
    'newyork': ('NY', None),
    'longisland': ('NY', None),
    'albany': ('NY', 'Albany'),
    'buffalo': ('NY', 'Erie'),
    'rochester': ('NY', 'Monroe'),
    'syracuse': ('NY', 'Onondaga'),
    'utica': ('NY', 'Oneida'),
    'hudsonvalley': ('NY', None),
    'catskills': ('NY', None),
    'newjersey': ('NJ', None),
    'jerseyshore': ('NJ', None),
    'newhaven': ('CT', 'New Haven'),
    'hartford': ('CT', 'Hartford'),
    'philadelphia': ('PA', 'Philadelphia'),
    'scranton': ('PA', 'Lackawanna'),
    'pittsburgh': ('PA', 'Allegheny'),
    'boston': ('MA', 'Suffolk'),
    'westernmass': ('MA', None),
    'burlington': ('VT', 'Chittenden'),
    'vermont': ('VT', None),
}

POST_ID_RE = re.compile(r'/(\d+)\.html$')

# Detail-page attribute patterns. Craigslist renders housing attrs as compact
# text like "3BR / 2Ba" and "1200ft2" (with markup that varies over time), so
# we regex over the flattened attribute text rather than fragile selectors.
FT2_RE = re.compile(r'([\d,]{2,7})\s*(?:ft2|ft²|sqft|sq\s?ft)', re.I)
BR_RE = re.compile(r'(\d+(?:\.\d+)?)\s*br\b', re.I)
BA_RE = re.compile(r'(\d+(?:\.\d+)?)\s*ba\b', re.I)
ZIP_RE = re.compile(r'\b(\d{5})\b')


@register
class CraigslistScraper(BaseScraper):
    name = 'craigslist'
    supported_regions = tuple(REGION_HINTS.keys())
    request_delay_seconds = 2.0

    def iter_listings(self, region: str) -> Iterable[ListingDTO]:
        if region not in REGION_HINTS:
            log.warning('Craigslist region %r has no hint; proceeding anyway', region)
        url = f'https://{region}.craigslist.org/search/{SECTION}'
        try:
            resp = self.get(url)
        except Exception as exc:
            log.warning('Craigslist fetch failed for %s: %s', region, exc)
            return
        yield from self._parse(resp.text, region)

    def _parse(self, html: str, region: str) -> Iterable[ListingDTO]:
        soup = BeautifulSoup(html, 'lxml')
        results = soup.select('li.cl-static-search-result')
        if not results:
            # Older/newer Craigslist markup fallback.
            results = soup.select('div.result-info, li.result-row')

        state_hint, county_hint = REGION_HINTS.get(region, (None, None))

        for el in results:
            link_el = el.find('a', href=True)
            if not link_el:
                continue
            href = link_el['href']
            if not href.startswith('http'):
                href = f'https://{region}.craigslist.org{href}'

            post_id = _extract_post_id(href)
            if not post_id:
                continue

            title_el = el.select_one('.title') or link_el
            title = title_el.get_text(strip=True) or 'Untitled listing'

            price_el = el.select_one('.price')
            price_cents = self._parse_price(price_el.get_text(strip=True)) if price_el else None

            location_el = el.select_one('.location')
            city = location_el.get_text(strip=True).strip('()') if location_el else None

            yield ListingDTO(
                source=self.name,
                source_listing_id=post_id,
                url=href,
                title=title,
                listing_type='sale',
                price_cents=price_cents,
                city=city,
                state=state_hint,
                county=county_hint,
                raw_payload={'region': region, 'section': SECTION},
            )

    def fetch_detail(self, dto: ListingDTO) -> ListingDTO:
        """Enrich a DTO from its Craigslist detail page.

        Pulls the street address and exact coordinates (straight from the map
        widget — no geocoding/billing needed), plus building sqft, beds/baths,
        and the post body. Any failure leaves ``dto`` as-is.
        """
        try:
            resp = self.get(dto.url)
        except Exception as exc:
            log.warning('Craigslist detail fetch failed for %s: %s', dto.url, exc)
            return dto

        soup = BeautifulSoup(resp.text, 'lxml')
        self._parse_detail(soup, dto)
        payload = dict(dto.raw_payload or {})
        payload['detail_fetched'] = True
        dto.raw_payload = payload
        return dto

    def _parse_detail(self, soup, dto: ListingDTO) -> None:
        # Exact coordinates from the map widget (no geocoding needed).
        map_el = soup.select_one('#map')
        if map_el:
            dto.lat = _to_float(map_el.get('data-latitude')) or dto.lat
            dto.lng = _to_float(map_el.get('data-longitude')) or dto.lng

        addr_el = soup.select_one('.mapaddress')
        if addr_el:
            addr = addr_el.get_text(' ', strip=True)
            if addr:
                dto.street = addr
                zip_m = ZIP_RE.search(addr)
                if zip_m:
                    dto.postal_code = zip_m.group(1)

        attrs_el = soup.select_one('.mapAndAttrs') or soup.select_one('.attrgroup')
        attrs_text = attrs_el.get_text(' ', strip=True) if attrs_el else ''
        if attrs_text:
            ft2_m = FT2_RE.search(attrs_text)
            if ft2_m:
                dto.building_sqft = _to_int(ft2_m.group(1))
            br_m = BR_RE.search(attrs_text)
            if br_m:
                dto.beds = _to_float(br_m.group(1))
            ba_m = BA_RE.search(attrs_text)
            if ba_m:
                dto.baths_total = _to_float(ba_m.group(1))

        body_el = soup.select_one('#postingbody')
        if body_el:
            dto.description = body_el.get_text('\n', strip=True) or dto.description

    @staticmethod
    def _parse_price(text: str) -> int | None:
        digits = re.sub(r'[^\d]', '', text or '')
        if not digits:
            return None
        try:
            return int(digits) * 100  # store as cents
        except ValueError:
            return None


def _extract_post_id(href: str) -> str | None:
    """Stable post id from a result href.

    Craigslist's current static-search markup links to
    ``/view/d/<slug>/<token>`` (a base62 token); older markup used
    ``/.../<digits>.html``. Handle both, preferring the legacy numeric id
    when present, else the final path segment (the token).
    """
    path = urlparse(href).path
    m = POST_ID_RE.search(path)
    if m:
        return m.group(1)
    segments = [seg for seg in path.split('/') if seg]
    return segments[-1] if segments else None


def _to_int(text: str | None) -> int | None:
    digits = re.sub(r'[^\d]', '', text or '')
    return int(digits) if digits else None


def _to_float(text: str | None) -> float | None:
    if text in (None, ''):
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None
