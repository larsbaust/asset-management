from flask import Blueprint, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_login import current_user
from datetime import datetime

# SocketIO-Objekt muss im Haupt-App-Init erstellt und importiert werden
socketio = SocketIO(cors_allowed_origins="*")

chat_bp = Blueprint('chat', __name__)

# User-Status-Tracking (im Speicher, für Demo-Zwecke)
online_users = {}

def get_status(uid):
    return online_users.get(uid, {}).get('status', 'offline')

from app.models import User

@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        return False  # block connection
    online_users[current_user.id] = {'status': 'online', 'username': current_user.username}
    # Hole alle User aus der DB
    all_users = User.query.all()
    user_list = []
    for user in all_users:
        status = online_users.get(user.id, {}).get('status', 'offline')
        user_list.append({'user_id': user.id, 'username': user.username, 'status': status})
    emit('online_users', user_list)
    emit('user_status', {'user_id': current_user.id, 'status': 'online'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated and current_user.id in online_users:
        online_users[current_user.id]['status'] = 'offline'
        emit('user_status', {'user_id': current_user.id, 'status': 'offline'}, broadcast=True)

@socketio.on('set_status')
def set_status(data):
    # data = {'status': 'away'/'online'}
    if current_user.is_authenticated and current_user.id in online_users:
        online_users[current_user.id]['status'] = data.get('status', 'online')
        emit('user_status', {'user_id': current_user.id, 'status': data.get('status', 'online')}, broadcast=True)

@socketio.on('send_message')
def handle_send_message(data):
    # data = {'to': user_id, 'msg': text}
    if current_user.is_authenticated:
        msg = {
            'from': current_user.id,
            'to': data['to'],
            'msg': data['msg'],
            'timestamp': datetime.utcnow().isoformat(),
            'from_username': current_user.username
        }
        emit('receive_message', msg, room=str(data['to']))
        emit('receive_message', msg, room=str(current_user.id))  # echo to sender

@socketio.on('join_room')
def on_join_room(data):
    join_room(str(current_user.id))

@chat_bp.route('/chat_widget')
def chat_widget():
    return render_template('chat_widget.html')
