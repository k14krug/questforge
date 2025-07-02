import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

db = SQLAlchemy()

def init_db(app: Flask):
    """
    Initializes the database with the Flask app.
    """
    # The SQLALCHEMY_DATABASE_URI should already be set by app.config.from_object(config_by_name[env_name])
    # in app.py, so we should not overwrite it here.
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False # This can remain
    db.init_app(app)

    with app.app_context():
        # db.create_all() is typically used for initial table creation without migrations.
        # With Flask-Migrate, 'flask db upgrade' handles table creation and schema updates.
        # We will remove this to avoid conflicts with migrations.
        pass
