"""Listing-source adapter registry.

Each concrete scraper subclasses `BaseScraper` and registers via the
`@register` decorator. The ingest task looks adapters up by name.
"""

from flaskblog.sources.base import BaseScraper, ListingDTO

_REGISTRY: dict[str, type[BaseScraper]] = {}


def register(scraper_cls: type[BaseScraper]) -> type[BaseScraper]:
    _REGISTRY[scraper_cls.name] = scraper_cls
    return scraper_cls


def get_scraper(name: str) -> BaseScraper:
    if name not in _REGISTRY:
        # Trigger import of submodules so they self-register.
        _load_all()
    if name not in _REGISTRY:
        raise KeyError(f"Unknown source: {name!r}. Known: {list(_REGISTRY)}")
    return _REGISTRY[name]()


def all_scrapers() -> dict[str, type[BaseScraper]]:
    _load_all()
    return dict(_REGISTRY)


def _load_all() -> None:
    from flaskblog.sources import craigslist  # noqa: F401


__all__ = ['BaseScraper', 'ListingDTO', 'register', 'get_scraper', 'all_scrapers']
