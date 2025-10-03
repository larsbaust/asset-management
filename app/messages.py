from flask import Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import db, User, Message
from datetime import datetime
import os

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/messages/inbox')
@login_required
def inbox():
    md3 = request.args.get('md3', type=int)
    messages = Message.query.filter_by(recipient_id=current_user.id).order_by(Message.timestamp.desc()).all()
    template = 'md3/messages/inbox.html' if md3 else 'messages/inbox.html'
    return render_template(template, messages=messages)

@messages_bp.route('/messages/sent')
@login_required
def sent():
    md3 = request.args.get('md3', type=int)
    messages = Message.query.filter_by(sender_id=current_user.id).order_by(Message.timestamp.desc()).all()
    template = 'md3/messages/sent.html' if md3 else 'messages/sent.html'
    return render_template(template, messages=messages)

@messages_bp.route('/messages/compose', methods=['GET', 'POST'])
@login_required
def compose():
    md3 = request.values.get('md3', type=int)
    users = User.query.filter(User.id != current_user.id).all()
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id')
        subject = request.form.get('subject')
        body = request.form.get('body')
        file = request.files.get('attachment')
        attachment_filename = None
        attachment_path = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'messages')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            attachment_filename = filename
            attachment_path = os.path.join('messages', filename)
        msg = Message(
            sender_id=current_user.id,
            recipient_id=int(recipient_id),
            subject=subject,
            body=body,
            timestamp=datetime.utcnow(),
            attachment_filename=attachment_filename,
            attachment_path=attachment_path
        )
        db.session.add(msg)
        db.session.commit()
        flash('Nachricht gesendet!', 'success')
        return redirect(url_for('messages.sent', md3=1 if md3 else None))
    template = 'md3/messages/compose.html' if md3 else 'messages/compose.html'
    return render_template(template, users=users)

@messages_bp.route('/messages/<int:message_id>', methods=['GET', 'POST'])
@login_required
def view_message(message_id):
    md3 = request.values.get('md3', type=int)
    msg = Message.query.get_or_404(message_id)
    if msg.recipient_id == current_user.id and not msg.is_read:
        msg.is_read = True
        db.session.commit()
    if request.method == 'POST':
        # Antwortfunktion
        subject = request.form.get('subject')
        body = request.form.get('body')
        file = request.files.get('attachment')
        attachment_filename = None
        attachment_path = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'messages')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            attachment_filename = filename
            attachment_path = os.path.join('messages', filename)
        reply = Message(
            sender_id=current_user.id,
            recipient_id=int(msg.sender_id),
            subject=subject,
            body=body,
            timestamp=datetime.utcnow(),
            attachment_filename=attachment_filename,
            attachment_path=attachment_path,
            reply_to_id=msg.id
        )
        db.session.add(reply)
        db.session.commit()
        flash('Antwort gesendet!', 'success')
        return redirect(url_for('messages.sent', md3=1 if md3 else None))
    template = 'md3/messages/view_message.html' if md3 else 'messages/view_message.html'
    return render_template(template, msg=msg)

@messages_bp.route('/messages/attachment/<path:filename>')
@login_required
def download_attachment(filename):
    upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'messages')
    return send_from_directory(upload_folder, filename, as_attachment=True)
