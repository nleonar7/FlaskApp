"""Pluggable relative-value scorers.

A scorer turns raw PLUTO lots into a ranked list of opportunities. The first
one, :class:`UnderbuiltInfillScorer`, ranks lots by unused buildable floor
area (development upside), after filtering out the parcels a naive
``max_far * lot_area`` ranking wrongly surfaces — cemeteries, parks, transit
yards, and other government/institutional land that will never be privately
redeveloped.

Metric math lives in :mod:`flaskblog.ranking.pluto`; this module owns the
*selection* policy (which lots count) and the *ranking* order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from flaskblog.models import NycPlutoLot
from flaskblog.ranking import pluto

# PLUTO land-use codes that could realistically be (re)developed: residential
# (01-04), commercial/office (05), industrial (06), and vacant land (11).
# Excludes transportation/utility (07), public/institutional (08), open space
# (09), and parking (10).
DEVELOPABLE_LAND_USES = ('01', '02', '03', '04', '05', '06', '11')

# Owner-name fragments marking parcels that won't be privately redeveloped.
_GOV_OWNER_RE = re.compile(
    r'CITY OF NEW YORK|NYC |PARKS|DEPT|DEPARTMENT|AUTHORITY|\bMTA\b'
    r'|STATE OF|TRANSIT|HOUSING',
    re.IGNORECASE,
)


@dataclass
class ScoredLot:
    """A lot plus the metrics that justify its rank."""
    lot: NycPlutoLot
    score: float             # ranking value (here: buildable sqft remaining)
    buildable_sqft: float
    pct_far_used: float

    def as_row(self) -> dict:
        """Flatten to a dict for tables / DataFrames / JSON."""
        lot = self.lot
        return {
            'bbl': lot.bbl,
            'borough': lot.borough,
            'address': lot.address,
            'zone_dist1': lot.zone_dist1,
            'land_use': lot.land_use,
            'lot_area': lot.lot_area,
            'bldg_area': lot.bldg_area,
            'built_far': lot.built_far,
            'max_far': lot.max_far,
            'pct_far_used': self.pct_far_used,
            'buildable_sqft_remaining': self.buildable_sqft,
            'assess_tot': lot.assess_tot,
            'score': self.score,
        }


def is_gov_owned(lot: NycPlutoLot) -> bool:
    return bool(lot.owner_name and _GOV_OWNER_RE.search(lot.owner_name))


class UnderbuiltInfillScorer:
    """Rank developable lots by unused buildable floor area.

    A lot qualifies when it is a developable land use, has a footprint in
    ``[min_lot_area, max_lot_area]`` sqft, is not government/institutional,
    and has used less than ``max_pct_far_used`` of its allowable FAR. The
    score is the remaining buildable square footage (higher = more upside).
    """

    name = 'underbuilt_infill'

    def __init__(
        self,
        *,
        min_lot_area: int = 2000,
        max_lot_area: int = 20000,
        max_pct_far_used: float = 0.5,
    ):
        self.min_lot_area = min_lot_area
        self.max_lot_area = max_lot_area
        self.max_pct_far_used = max_pct_far_used

    def _candidate_query(self, boroughs: Iterable[str] | None):
        """SQL prefilter for the cheap, index-friendly predicates."""
        q = NycPlutoLot.query.filter(
            NycPlutoLot.land_use.in_(DEVELOPABLE_LAND_USES),
            NycPlutoLot.lot_area >= self.min_lot_area,
            NycPlutoLot.lot_area <= self.max_lot_area,
        )
        if boroughs:
            q = q.filter(NycPlutoLot.borough.in_(tuple(boroughs)))
        return q

    def score_lot(self, lot: NycPlutoLot) -> ScoredLot | None:
        """Return a ScoredLot if the lot qualifies, else None."""
        if is_gov_owned(lot):
            return None
        pct = pluto.pct_far_used(lot)
        if pct is None or pct >= self.max_pct_far_used:
            return None
        buildable = pluto.buildable_sqft_remaining(lot)
        if not buildable:  # None or 0
            return None
        return ScoredLot(lot=lot, score=buildable, buildable_sqft=buildable, pct_far_used=pct)

    def rank(self, *, limit: int = 50, boroughs: Iterable[str] | None = None) -> list[ScoredLot]:
        """Return the top ``limit`` qualifying lots, best first."""
        scored: list[ScoredLot] = []
        for lot in self._candidate_query(boroughs):
            result = self.score_lot(lot)
            if result is not None:
                scored.append(result)
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:limit]
