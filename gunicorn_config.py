import multiprocessing
import os

# Basic server configuration
bind = "0.0.0.0:5014"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"  # Use "eventlet" if you want async support

# Logging configuration
accesslog = "/home/kkrug/projects/questforge/logs/gunicorn_access.log"
errorlog = "/home/kkrug/projects/questforge/logs/gunicorn_error.log"
loglevel = "debug"
capture_output = True  # Redirect stdout/stderr to error log

# Capture Flask application logging
# This will redirect your Flask app.logger messages to Gunicorn's error log
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'filename': '/home/kkrug/projects/questforge/logs/campaign_service.log',
            'mode': 'a',
        }
    },
    'loggers': {
        'gunicorn.error': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        '': {  # Root logger
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
        },
    }
}

# Create log directory if it doesn't exist
os.makedirs(os.path.dirname(accesslog), exist_ok=True)