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

def create_app(config_name=None):
    app = Flask(__name__)
    app.jinja_env.filters['datetimeformat'] = datetimeformat

    # Determine config name from environment variable if not provided
    if config_name is None:
        config_name = os.getenv('APP_ENV', 'development')

    # Load config based on config_name
    from config import config_by_name
    if config_name not in config_by_name:
        raise ValueError(f"Invalid APP_ENV '{config_name}'. Must be one of: {list(config_by_name.keys())}")
    app.config.from_object(config_by_name[config_name])

    # --- Standard Flask Logging Setup ---
    log_dir = os.path.join(app.instance_path, 'logs')
    os.makedirs(log_dir, exist_ok=True) # Ensure log directory exists

    # Define handlers
    log_file_path = os.path.join(log_dir, 'questforge.log')
    file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setLevel(getattr(logging, app.config.get('LOGLEVEL', 'INFO')))
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'
    ))

    console_handler = StreamHandler()
    console_handler.setLevel(getattr(logging, app.config.get('LOGLEVEL', 'INFO')))
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - CONSOLE - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'
    ))

    while app.logger.handlers:
        app.logger.removeHandler(app.logger.handlers[0])
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    app.logger.setLevel(getattr(logging, app.config.get('LOGLEVEL', 'INFO')))

    app.logger.info('--- Standard Flask logging initialized ---')
    # --- End Standard Flask Logging Setup ---

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio = init_socketio(app)

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
