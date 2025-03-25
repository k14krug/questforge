import sys
import os

# Add the parent directory to the path BEFORE imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from flask import Flask
from questforge.extensions import db

@pytest.fixture(scope='session')
def app():
    """Create a Flask app for testing."""
    app = Flask('test_app')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def db_session(app):
    """Create a fresh database session for each test."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        yield db.session
        
        db.session.close()
        transaction.rollback()
        connection.close()