"""Deterministic tests for the Craigslist detail-page parser.

Exercises `CraigslistScraper._parse_detail` against a representative fixture so
the field extraction (coords, address, sqft, beds/baths) is verified without
hitting the live site.
"""

from bs4 import BeautifulSoup

from flaskblog.sources.base import ListingDTO
from flaskblog.sources.craigslist import CraigslistScraper, _extract_post_id

DETAIL_HTML = """
<html><body>
  <section class="body">
    <div class="mapAndAttrs">
      <div class="mapbox">
        <div id="map" data-latitude="40.6402" data-longitude="-74.0764"
             data-accuracy="10"></div>
        <div class="mapaddress">245 Bay Street, Staten Island, NY 10301</div>
      </div>
      <p class="attrgroup">
        <span class="attr">3BR / 2Ba</span>
        <span class="attr">1,200ft2</span>
      </p>
    </div>
    <section id="postingbody">
      QR Code Link to This Post
      Renovated two-family near the ferry. Must see.
    </section>
  </section>
</body></html>
"""


def _detail_dto():
    dto = ListingDTO(
        source='craigslist',
        source_listing_id='7777777777',
        url='https://newyork.craigslist.org/stn/reo/7777777777.html',
        title='2-family near ferry',
    )
    scraper = CraigslistScraper()
    soup = BeautifulSoup(DETAIL_HTML, 'lxml')
    scraper._parse_detail(soup, dto)
    return dto


def test_detail_extracts_coordinates_from_map_widget():
    dto = _detail_dto()
    assert dto.lat == 40.6402
    assert dto.lng == -74.0764


def test_detail_extracts_address_and_zip():
    dto = _detail_dto()
    assert dto.street == '245 Bay Street, Staten Island, NY 10301'
    assert dto.postal_code == '10301'


def test_detail_extracts_sqft_beds_baths():
    dto = _detail_dto()
    assert dto.building_sqft == 1200  # comma stripped
    assert dto.beds == 3.0
    assert dto.baths_total == 2.0


def test_detail_extracts_description():
    dto = _detail_dto()
    assert 'near the ferry' in dto.description


def test_extract_post_id_handles_both_url_formats():
    # Current markup: /view/d/<slug>/<base62-token>
    new_url = 'https://www.craigslist.org/view/d/beautiful-furnished/jKs2QhYhHpkripwhtTWAFb'
    assert _extract_post_id(new_url) == 'jKs2QhYhHpkripwhtTWAFb'
    # Legacy markup: /.../<digits>.html
    old_url = 'https://newyork.craigslist.org/stn/reo/d/staten-island/7778889999.html'
    assert _extract_post_id(old_url) == '7778889999'


def test_detail_is_resilient_to_missing_fields():
    dto = ListingDTO(source='craigslist', source_listing_id='1', url='x', title='t')
    scraper = CraigslistScraper()
    scraper._parse_detail(BeautifulSoup('<html></html>', 'lxml'), dto)
    assert dto.street is None
    assert dto.building_sqft is None
    assert dto.lat is None
