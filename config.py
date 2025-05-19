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
    # Model used for critical, logic-heavy AI calls (e.g., campaign generation, main narrative responses)
    OPENAI_MODEL_LOGIC = os.environ.get('OPENAI_MODEL_LOGIC') or 'gpt-4.1'

    # Model used for less critical AI calls (e.g., character naming, hints, plot point checks, historical summary)
    OPENAI_MODEL_MAIN = os.environ.get('OPENAI_MODEL_MAIN') or 'gpt-4.1-mini' # Corrected from gpt-4.1o-mini

    OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE') or 0.7)
    OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS') or 1024)

    # Gameplay settings
    MAX_HISTORICAL_SUMMARIES = int(os.environ.get('MAX_HISTORICAL_SUMMARIES') or 20) # Max historical summaries to keep in state

    # OpenAI Pricing (per 1K tokens) - **Update with actual values!**
    # Valitdation: 2025-05-15 kkrug
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
        # 'gpt-4.5': {'prompt': 0.075, 'completion': 0.15},  # Deprecated
    }
