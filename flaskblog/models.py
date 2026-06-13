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

