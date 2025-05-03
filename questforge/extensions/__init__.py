# Package initialization file for extensions
from .database import db
from .bcrypt import bcrypt
from flask_migrate import Migrate
from flask_login import LoginManager
from .socketio import socketio, init_socketio

migrate = Migrate()
login_manager = LoginManager()
