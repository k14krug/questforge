from flask import Flask, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return "QuestForge Backend is running!"

if __name__ == '__main__':
    socketio.run(app, debug=True)
