import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_that_should_be_changed_in_production'
    # Add other configuration variables here as needed, e.g., database URI, AI API keys
