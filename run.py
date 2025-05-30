from app import create_app
from app.chat_socket import socketio

app = create_app()
socketio.init_app(app)

if __name__ == '__main__':
    socketio.run(app, debug=True)
