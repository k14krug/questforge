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
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL') or 'gpt-4o-mini'
    OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE') or 0.7)
    OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS') or 1024)

    # OpenAI Pricing (per 1K tokens) - **Update with actual values!**
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
        'gpt-4.5': {'prompt': 0.075, 'completion': 0.15},
    }
