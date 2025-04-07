from flask_socketio import SocketIO
from flask import current_app

socketio = SocketIO()

def get_socketio():
    """Get the socketio instance"""
    return socketio

def init_socketio(app):
    """Initialize Socket.IO with the Flask application"""
    # Store config in app context
    app.config.setdefault('SOCKETIO_CORS_ORIGINS', [])
    app.config.setdefault('SOCKETIO_LOGGING', False)
    app.config.setdefault('ENGINEIO_LOGGING', False)
    app.config.setdefault('SOCKETIO_ASYNC_MODE', 'threading')
    
    print(f"Initializing SocketIO with:")
    print(f"  CORS Origins: {app.config['SOCKETIO_CORS_ORIGINS']}")
    print(f"  SocketIO Logging: {app.config['SOCKETIO_LOGGING']}")
    print(f"  EngineIO Logging: {app.config['ENGINEIO_LOGGING']}")
    print(f"  Async Mode: {app.config['SOCKETIO_ASYNC_MODE']}")

    socketio.init_app(
        app,
        cors_allowed_origins=app.config['SOCKETIO_CORS_ORIGINS'],
        logger=app.config['SOCKETIO_LOGGING'],
        engineio_logger=app.config['ENGINEIO_LOGGING'],
        async_mode=app.config['SOCKETIO_ASYNC_MODE']
    )
    
    return socketio
