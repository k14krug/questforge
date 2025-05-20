import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SOCKETIO_CORS_ORIGINS = os.environ.get('SOCKETIO_CORS_ORIGINS', 'http://localhost')  # Default to localhost
    SOCKETIO_LOGGING = False
    ENGINEIO_LOGGING = False
    OPENAI_MODEL_LOGIC = os.environ.get('OPENAI_MODEL_LOGIC', 'gpt-4.1')
    OPENAI_MODEL_MAIN = os.environ.get('OPENAI_MODEL_MAIN', 'gpt-4.1-mini')
    OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', 0.7))
    OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', 1024))
    MAX_HISTORICAL_SUMMARIES = int(os.environ.get('MAX_HISTORICAL_SUMMARIES', 20))
    OPENAI_PRICING = {
        'gpt-3.5-turbo': {'prompt': 0.0015, 'completion': 0.002},
        'gpt-4': {'prompt': 0.03, 'completion': 0.06},
        'gpt-4-32k': {'prompt': 0.06, 'completion': 0.12},
        'gpt-4-turbo': {'prompt': 0.01, 'completion': 0.03},
        'gpt-4o': {'prompt': 0.0025, 'completion': 0.01},
        'gpt-4o-mini': {'prompt': 0.00015, 'completion': 0.0006},
        'gpt-4.1': {'prompt': 0.002, 'completion': 0.008},
        'gpt-4.1-mini': {'prompt': 0.0004, 'completion': 0.0016},
        'gpt-4.1-nano': {'prompt': 0.0001, 'completion': 0.0004},
    }

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = True
    LOGLEVEL = 'DEBUG'
    SOCKETIO_CORS_ORIGINS = "*"  # Allow all origins for development
    SOCKETIO_LOGGING = True
    ENGINEIO_LOGGING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URI') 
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-123'

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    LOGLEVEL = 'INFO'
    SOCKETIO_CORS_ORIGINS = os.environ.get('SOCKETIO_CORS_ORIGINS', 'https://your-production-domain.com')
    SOCKETIO_LOGGING = False
    ENGINEIO_LOGGING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('PROD_DATABASE_URL')

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
