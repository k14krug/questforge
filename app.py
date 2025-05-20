from questforge import create_app
from questforge.extensions import socketio
import os

app = create_app()

if __name__ == '__main__':
    port = 5014 if os.getenv('APP_ENV', 'development') == 'development' else 5004
    debug = True if os.getenv('APP_ENV', 'development') == 'development' else False
    socketio.run(app, port=port, debug=debug)
