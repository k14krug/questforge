import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-123'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://questforge_user:admin14@localhost/questforge_dev'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SocketIO settings
    SOCKETIO_CORS_ORIGINS = "*" # Allow all origins for development
    SOCKETIO_LOGGING = True # Enable SocketIO logging for debugging
    ENGINEIO_LOGGING = True # Enable EngineIO logging for debugging

    # OpenAI settings
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL') or 'gpt-3.5-turbo'
    OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE') or 0.7)
    OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS') or 1024)
