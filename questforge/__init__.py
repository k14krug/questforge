import logging
import os
from logging import StreamHandler # Import StreamHandler
from logging.handlers import RotatingFileHandler # Import RotatingFileHandler
from flask import Flask
from .extensions import db, login_manager, bcrypt, migrate, init_socketio
from .services.socket_service import SocketService

from datetime import datetime

def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ""
    try:
        return value.strftime(format)
    except Exception:
        return str(value)

def create_app(config_name='default'):
    app = Flask(__name__)
    app.jinja_env.filters['datetimeformat'] = datetimeformat

    # Load config
    app.config.from_object('config.Config')

    # --- Standard Flask Logging Setup ---
    log_dir = os.path.join(app.instance_path, 'logs')
    os.makedirs(log_dir, exist_ok=True) # Ensure log directory exists

    # Define handlers
    # Use RotatingFileHandler for the file logger
    log_file_path = os.path.join(log_dir, 'questforge.log') # Use a more general log file name
    # Rotate logs at 5MB, keep 3 backups
    file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=3) 
    file_handler.setLevel(logging.DEBUG) # Log DEBUG and above to file
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]' # Add path/line info
    ))

    console_handler = StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - CONSOLE - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'
    ))

    # Remove default handlers and add ours to app.logger
    while app.logger.handlers:
        app.logger.removeHandler(app.logger.handlers[0])
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Set the app logger level to DEBUG to allow file handler to process debug messages
    app.logger.setLevel(logging.DEBUG)

    app.logger.info('--- Standard Flask logging initialized ---')
    # --- End Standard Flask Logging Setup ---

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio = init_socketio(app) # SocketIO initialized after logging

    # Set login view
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register user_loader
    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        return User.query.get(int(user_id))

    # Register blueprints
    from .views.auth import auth_bp
    from .views.main import main_bp
    from .views.campaign_api import campaign_api_bp
    from .views.game import game_bp
    from .views.template import template_bp
    from .views.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(campaign_api_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(template_bp)
    app.register_blueprint(admin_bp)

    # Register socket handlers
    SocketService.register_handlers()

    return app
