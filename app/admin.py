from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .models import User, db
from .forms import RegisterForm

admin = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator für Admin-Zugriff
from functools import wraps
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Zugriff verweigert: Nur für Admins!', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/users')
@login_required
@admin_required
def user_management():
    users = User.query.order_by(User.id).all()
    return render_template('admin/user_management.html', users=users)

@admin.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    import os
    from werkzeug.utils import secure_filename
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Benutzername bereits vergeben.', 'danger')
            return render_template('admin/add_user.html', form=form)
        user = User(
            username=form.username.data,
            role=form.role.data,
            vorname=form.vorname.data,
            nachname=form.nachname.data,
            email=form.email.data,
            street=form.street.data,
            postal_code=form.postal_code.data,
            city=form.city.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)
        # Profilbild speichern
        if form.profile_image.data:
            filename = secure_filename(form.profile_image.data.filename)
            img_path = os.path.join('static/profile_images', filename)
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            form.profile_image.data.save(img_path)
            user.profile_image = filename
        db.session.add(user)
        db.session.commit()
        flash('Benutzer erfolgreich angelegt.', 'success')
        return redirect(url_for('admin.user_management'))
    return render_template('admin/add_user.html', form=form)

@admin.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    import os
    from werkzeug.utils import secure_filename
    user = User.query.get_or_404(user_id)
    form = RegisterForm(obj=user)
    if request.method == 'POST' and form.validate_on_submit():
        user.username = form.username.data
        user.role = form.role.data
        user.vorname = form.vorname.data
        user.nachname = form.nachname.data
        user.email = form.email.data
        user.street = form.street.data
        user.postal_code = form.postal_code.data
        user.city = form.city.data
        user.phone = form.phone.data
        if form.password.data:
            user.set_password(form.password.data)
        # Profilbild speichern
        if form.profile_image.data:
            filename = secure_filename(form.profile_image.data.filename)
            img_path = os.path.join('static/profile_images', filename)
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            form.profile_image.data.save(img_path)
            user.profile_image = filename
        db.session.commit()
        flash('Benutzerdaten aktualisiert.', 'success')
        return redirect(url_for('admin.user_management'))
    form.password.data = ''
    return render_template('admin/edit_user.html', form=form, user=user)

@admin.route('/users/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        flash('Der Haupt-Admin kann nicht gelöscht werden.', 'danger')
        return redirect(url_for('admin.user_management'))
    db.session.delete(user)
    db.session.commit()
    flash('Benutzer gelöscht.', 'success')
    return redirect(url_for('admin.user_management'))
