import os

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

if os.environ.get("FLASK_ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv(override=True)


app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

_uri = os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_DATABASE_URI')
if _uri and _uri.startswith('postgres://'):
    _uri = _uri.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = 'smtp.live.com'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD')

app.config['CELERY_BROKER_URL'] = os.environ.get(
    'CELERY_BROKER_URL', 'redis://localhost:6379/0'
)
app.config['CELERY_RESULT_BACKEND'] = os.environ.get(
    'CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'
)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
mail = Mail(app)
migrate = Migrate(app, db)


from flaskblog import routes  # noqa: E402,F401
from flaskblog import models  # noqa: E402,F401  (ensure models register with SQLAlchemy)
