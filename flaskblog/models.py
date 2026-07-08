from itsdangerous import URLSafeTimedSerializer as Serializer
from datetime import datetime
from sqlalchemy import Index, UniqueConstraint
from flaskblog import db, login_manager, app
from flask_login import UserMixin


LISTING_TYPES = ('sale', 'land', 'rent', 'auction')
LISTING_STATUSES = ('active', 'pending', 'sold', 'withdrawn')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(60), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    highest_rent = db.Column(db.Integer, nullable=False)
    posts = db.relationship('BlogPost', backref='author', lazy=True)
    ratings = db.relationship('ApartmentScore', backref='author', lazy=True)
    admin = db.Column(db.Boolean)


    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=expires_sec)['user_id']
        except Exception:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}', '{self.highest_rent}', '{self.admin}')"

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"BlogPost('{self.title}', '{self.date_posted}')"


class Apartment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    link = db.Column(db.String, nullable=False)
    monthly_cost = db.Column(db.Integer, nullable=False)
    city = db.Column(db.String, nullable=False)
    scores = db.relationship('ApartmentScore', backref='title', lazy=True)

    def __repr__(self):
        return f"Apartment('{self.title}')"


class ApartmentScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_score = db.Column(db.Integer, nullable=False)
    price_score = db.Column(db.Integer, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    apartment_id = db.Column(db.Integer, db.ForeignKey('apartment.id'), nullable=False)

    def __repr__(self):
        return f"ApartmentScore('{self.title}', '{self.author.email}')"


class Listing(db.Model):
    __tablename__ = 'listing'

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(40), nullable=False)
    source_listing_id = db.Column(db.String(120), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(300), nullable=False)

    listing_type = db.Column(db.String(20), nullable=False, default='sale')
    status = db.Column(db.String(20), nullable=False, default='active')

    price_cents = db.Column(db.BigInteger)

    street = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    postal_code = db.Column(db.String(15))
    county = db.Column(db.String(100))

    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

    lot_sqft = db.Column(db.Integer)
    building_sqft = db.Column(db.Integer)
    acres = db.Column(db.Float)

    beds = db.Column(db.Float)
    baths_total = db.Column(db.Float)
    year_built = db.Column(db.Integer)

    zoning_code = db.Column(db.String(40))
    far_max = db.Column(db.Float)

    description = db.Column(db.Text)
    raw_payload = db.Column(db.JSON)

    first_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('source', 'source_listing_id', name='uq_listing_source_pair'),
        Index('ix_listing_state_price', 'state', 'price_cents'),
        Index('ix_listing_state_county', 'state', 'county'),
        Index('ix_listing_status', 'status'),
    )

    @property
    def price_dollars(self):
        return None if self.price_cents is None else self.price_cents / 100

    def __repr__(self):
        return f"Listing({self.source}:{self.source_listing_id} {self.title!r})"


class GeocodeCache(db.Model):
    __tablename__ = 'geocode_cache'

    id = db.Column(db.Integer, primary_key=True)
    address_key = db.Column(db.String(500), unique=True, nullable=False)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    geocoded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"GeocodeCache({self.address_key!r} -> {self.lat},{self.lng})"


class NycPlutoLot(db.Model):
    """A NYC tax lot from the PLUTO dataset, keyed by BBL.

    PLUTO (Primary Land Use Tax Lot Output) is NYC's authoritative tax-lot
    dataset. We store a curated subset of its ~90 columns plus a raw_payload
    escape hatch. Used as source-of-truth for lot/building area and FAR
    (floor-area-ratio) so we can spot under-built lots (built FAR << max FAR
    = development upside) and, later, listing-vs-record discrepancies.
    """

    __tablename__ = 'nyc_pluto_lot'

    # Borough-Block-Lot, the natural key. Stored as a 10-char string so
    # leading zeros survive and Socrata's numeric coercion can't corrupt it.
    bbl = db.Column(db.String(10), primary_key=True)

    # Identity / address (for GeoSearch join-back and display).
    borough = db.Column(db.String(2))          # 'MN','BX','BK','QN','SI'
    block = db.Column(db.Integer)
    lot = db.Column(db.Integer)
    address = db.Column(db.String(200))
    zipcode = db.Column(db.String(10))

    # Areas (square feet) — the source of truth for sqft discrepancies.
    lot_area = db.Column(db.Integer)           # lotarea
    bldg_area = db.Column(db.Integer)          # bldgarea (total gross floor area)
    com_area = db.Column(db.Integer)           # comarea
    res_area = db.Column(db.Integer)           # resarea
    num_floors = db.Column(db.Float)           # numfloors (can be fractional)
    units_res = db.Column(db.Integer)          # unitsres
    units_total = db.Column(db.Integer)        # unitstotal
    year_built = db.Column(db.Integer)         # yearbuilt

    # FAR / zoning — the development-upside core.
    built_far = db.Column(db.Float)            # builtfar
    resid_far = db.Column(db.Float)            # residfar
    comm_far = db.Column(db.Float)             # commfar
    facil_far = db.Column(db.Float)            # facilfar
    land_use = db.Column(db.String(2))         # landuse
    zone_dist1 = db.Column(db.String(20))      # zonedist1

    # Value context.
    owner_name = db.Column(db.String(200))     # ownername
    assess_land = db.Column(db.BigInteger)     # assessland (dollars)
    assess_tot = db.Column(db.BigInteger)      # assesstot (dollars)

    lat = db.Column(db.Float)                  # latitude (ships with PLUTO)
    lng = db.Column(db.Float)                  # longitude

    # Provenance.
    pluto_version = db.Column(db.String(12))   # e.g. '25v1'
    raw_payload = db.Column(db.JSON)           # full source row
    ingested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_pluto_borough', 'borough'),
        Index('ix_pluto_zonedist1', 'zone_dist1'),
        Index('ix_pluto_landuse', 'land_use'),
        # Accelerates the under-built ranking scan.
        Index('ix_pluto_far', 'resid_far', 'built_far'),
    )

    @property
    def max_far(self):
        """The greatest of the three allowable FARs, or None if unknown."""
        vals = [v for v in (self.resid_far, self.comm_far, self.facil_far) if v]
        return max(vals) if vals else None

    def __repr__(self):
        return f"NycPlutoLot({self.bbl} {self.address!r})"


class BblCache(db.Model):
    """Caches address -> BBL resolutions from NYC Planning's free GeoSearch,
    so repeat lookups never re-hit the network. Mirrors GeocodeCache."""

    __tablename__ = 'bbl_cache'

    id = db.Column(db.Integer, primary_key=True)
    address_key = db.Column(db.String(500), unique=True, nullable=False)
    bbl = db.Column(db.String(10))
    confidence = db.Column(db.Float)
    resolved_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"BblCache({self.address_key!r} -> {self.bbl})"

