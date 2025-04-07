from questforge import create_app
from questforge.extensions import socketio

app = create_app() 

if __name__ == '__main__':
    socketio.run(app, port=5014, debug=True)
