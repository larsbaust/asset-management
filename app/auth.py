from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from .models import User
from . import db
from flask_mail import Message
from . import mail

auth = Blueprint('auth', __name__)

from .forms import LoginForm, RegisterForm, ResetPasswordForm
from werkzeug.security import generate_password_hash

@auth.route('/login', methods=['GET', 'POST'])
def login():
    md3 = request.values.get('md3', type=int, default=1)  # Default zu MD3
    from datetime import datetime, timedelta
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        now = datetime.utcnow()
        if user:
            # Prüfe, ob gesperrt
            if user.lock_until and user.lock_until > now:
                minutes = int((user.lock_until - now).total_seconds() // 60) + 1
                flash(f'Zu viele Fehlversuche. Account gesperrt für {minutes} Minuten.', 'error')
                template = 'md3/auth/login.html' if md3 else 'auth/login.html'
                return render_template(template, form=form)
            if user.check_password(form.password.data):
                user.failed_logins = 0
                user.lock_until = None
                db.session.commit()
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                # Preserve md3 parameter in redirect if present
                if next_page and md3:
                    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
                    parsed = list(urlparse(next_page))
                    qs = parse_qs(parsed[4])
                    qs['md3'] = '1'
                    parsed[4] = urlencode(qs, doseq=True)
                    next_page = urlunparse(parsed)
                return redirect(next_page or url_for('main.index', md3=1 if md3 else None))
            else:
                user.failed_logins = (user.failed_logins or 0) + 1
                if user.failed_logins >= 5:
                    user.lock_until = now + timedelta(minutes=10)
                    flash('Zu viele Fehlversuche. Account für 10 Minuten gesperrt.', 'error')
                else:
                    flash('Bitte überprüfen Sie Ihre Anmeldedaten.', 'error')
                db.session.commit()
        else:
            flash('Bitte überprüfen Sie Ihre Anmeldedaten.', 'error')
    
    template = 'md3/auth/login.html' if md3 else 'auth/login.html'
    return render_template(template, form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    md3 = request.values.get('md3', type=int)
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Benutzername ist bereits vergeben.', 'error')
            template = 'md3/auth/register.html' if md3 else 'auth/register.html'
            return render_template(template, form=form)
        user = User(
            username=form.username.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registrierung erfolgreich! Du bist jetzt eingeloggt.', 'success')
        return redirect(url_for('main.index', md3=1 if md3 else None))
    template = 'md3/auth/register.html' if md3 else 'auth/register.html'
    return render_template(template, form=form)

@auth.route('/logout')
def logout():
    md3 = request.values.get('md3', type=int)
    logout_user()
    flash('Du wurdest erfolgreich abgemeldet.', 'success')
    return redirect(url_for('auth.login', md3=1 if md3 else None))

@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    md3 = request.values.get('md3', type=int)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_token()
            reset_link = url_for('auth.set_new_password', token=token, _external=True, md3=1 if md3 else None)
            # E-Mail senden
            msg = Message('Passwort zurücksetzen', recipients=[user.email])
            msg.body = f'''Hallo {user.username},

Um dein Passwort zurückzusetzen, klicke bitte auf den folgenden Link:
{reset_link}

Falls du kein Passwort-Reset angefordert hast, ignoriere diese E-Mail einfach.

Viele Grüße
Dein Team'''
            mail.send(msg)
        # Immer gleiches Feedback, egal ob User existiert (Sicherheit)
        flash('Wenn die E-Mail existiert, wurde ein Link zum Zurücksetzen gesendet.', 'info')
        return redirect(url_for('auth.login', md3=1 if md3 else None))
    template = 'md3/auth/reset_password.html' if md3 else 'auth/reset_password.html'
    return render_template(template, form=form)

from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

class SetNewPasswordForm(FlaskForm):
    password = PasswordField('Neues Passwort', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Passwort setzen')

@auth.route('/set_new_password/<token>', methods=['GET', 'POST'])
def set_new_password(token):
    md3 = request.values.get('md3', type=int)
    form = SetNewPasswordForm()
    user = User.verify_reset_token(token)
    if not user:
        flash('Der Link ist ungültig oder abgelaufen.', 'danger')
        return redirect(url_for('auth.reset_password', md3=1 if md3 else None))
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        # E-Mail-Benachrichtigung
        try:
            msg = Message('Dein Passwort wurde geändert', recipients=[user.email])
            msg.body = f'''Hallo {user.username},

Dein Passwort wurde soeben geändert. Falls du diese Änderung nicht selbst vorgenommen hast, kontaktiere bitte sofort den Administrator.

Viele Grüße
Dein Team'''
            mail.send(msg)
        except Exception as e:
            # Fehler beim Senden ignorieren, aber im Log festhalten
            print(f"Fehler beim Senden der Passwortänderungs-Benachrichtigung: {e}")
        flash('Passwort erfolgreich geändert! Du kannst dich jetzt einloggen.', 'success')
        return redirect(url_for('auth.login', md3=1 if md3 else None))
    template = 'md3/auth/set_new_password.html' if md3 else 'auth/set_new_password.html'
    return render_template(template, form=form)
