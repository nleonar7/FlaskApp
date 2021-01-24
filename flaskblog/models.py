from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from datetime import datetime
from flaskblog import db, login_manager, app
from flask_login import UserMixin


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
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
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

