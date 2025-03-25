import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-123'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://questforge_user:admin14@localhost/questforge_dev'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
