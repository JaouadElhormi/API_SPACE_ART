from src.app import create_app
from flask_socketio import SocketIO, emit

if __name__ == '__main__':
    app = create_app()
    app.run(app)