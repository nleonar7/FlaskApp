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

            m = POST_ID_RE.search(urlparse(href).path)
            if not m:
                continue
            post_id = m.group(1)

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

    @staticmethod
    def _parse_price(text: str) -> int | None:
        digits = re.sub(r'[^\d]', '', text or '')
        if not digits:
            return None
        try:
            return int(digits) * 100  # store as cents
        except ValueError:
            return None
