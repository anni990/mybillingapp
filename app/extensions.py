from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_session import Session

# Initialize extensions

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
session = Session()
