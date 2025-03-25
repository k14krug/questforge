from flask import Flask
from questforge.extensions import db, migrate, login_manager, bcrypt
from questforge.models.user import User
from questforge.models.game import Game
from questforge.models.template import Template

def create_app(config_class='config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Register blueprints
    from questforge.views.auth import auth_bp
    app.register_blueprint(auth_bp)

    return app
