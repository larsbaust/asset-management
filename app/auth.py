from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from .models import User
from . import db

auth = Blueprint('auth', __name__)

from .forms import LoginForm, RegisterForm, ResetPasswordForm
from werkzeug.security import generate_password_hash

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Bitte überprüfen Sie Ihre Anmeldedaten.', 'error')
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Benutzername ist bereits vergeben.', 'error')
            return render_template('auth/register.html', form=form)
        user = User(
            username=form.username.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registrierung erfolgreich! Du bist jetzt eingeloggt.', 'success')
        return redirect(url_for('main.index'))
    return render_template('auth/register.html', form=form)

@auth.route('/logout')
def logout():
    logout_user()
    flash('Du wurdest erfolgreich abgemeldet.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.email.data).first()
        # In einer echten App würdest du nach user.email suchen, aber das User-Modell hat aktuell nur username
        if user:
            # Demo-Link (Token-Logik kann später ergänzt werden)
            reset_link = url_for('auth.set_new_password', token='demo-token', _external=True)
            flash(f'Ein Link zum Zurücksetzen deines Passworts wurde gesendet: <a href="{reset_link}">Passwort jetzt zurücksetzen</a>', 'success')
        else:
            flash('Es wurde kein Benutzer mit dieser E-Mail gefunden.', 'danger')
    return render_template('auth/reset_password.html', form=form)

from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

class SetNewPasswordForm(FlaskForm):
    password = PasswordField('Neues Passwort', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Passwort setzen')

@auth.route('/set_new_password/<token>', methods=['GET', 'POST'])
def set_new_password(token):
    form = SetNewPasswordForm()
    if form.validate_on_submit():
        # Dummy-Logik: Setze Passwort für Demo-User
        user = User.query.filter_by(username='demo-user').first()
        if user:
            user.set_password(form.password.data)
            db.session.commit()
            flash('Dein Passwort wurde erfolgreich geändert.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Benutzer nicht gefunden.', 'danger')
    return render_template('auth/set_new_password.html', form=form)
