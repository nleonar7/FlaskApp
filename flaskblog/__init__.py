
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail

# Load .env for local/dev before app config
if os.environ.get("FLASK_ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()


app = Flask(__name__)
# Use environment variables for secrets
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
uri = os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_DATABASE_URI')
if uri and uri.startswith('postgres://'):
    uri = uri.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
app.config['MAIL_SERVER'] = 'smtp.live.com'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD')
mail = Mail(app)


#bellow is from  https://www.reddit.com/r/flask/comments/2vu3ft/af_having_trouble_getting_flask_mail_to_work_with/
#added this to try and get the blocked messages to send
MAIL_USE_TLS = False
MAIL_SUPPRESS_SEND = False
MAIL_DEBUG = True
TESTING = False




from flaskblog import routes

# Automatically create tables in dev/local
if os.environ.get("FLASK_ENV") != "production":
    with app.app_context():
        from flaskblog import models  # Ensure models are loaded
        db.create_all()



#https://www.youtube.com/watch?v=vutyTx7IaAI first comment indicates what you need to do to get the email to actually send for requesting a new email, currently bugs
