import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail

app = Flask(__name__)
app.config['SECRET_KEY'] = '88ae1cb251be78575246856c955f7104'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://bvnewsbxtddjsv:ce3f4f0c36e9611c224db96093b70167a2142a20dac6d850daadd1c245289db3@ec2-3-216-181-219.compute-1.amazonaws.com:5432/d115s3psivdfro'
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



#https://www.youtube.com/watch?v=vutyTx7IaAI first comment indicates what you need to do to get the email to actually send for requesting a new email, currently bugs
