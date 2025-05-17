from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .models import User, db
from .forms import RegisterForm, RoleForm

admin = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator für Admin-Zugriff
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Zugriff verweigert: Nicht eingeloggt!', 'danger')
            return redirect(url_for('main.index'))
        if not getattr(current_user, 'role', None):
            flash('Zugriff verweigert: Keine Rolle zugewiesen! Wende dich an den Administrator.', 'danger')
            return redirect(url_for('main.index'))
        if getattr(current_user.role, 'name', None) != 'Admin':
            flash(f'Zugriff verweigert: Nur für Admins! (Aktueller User: {current_user.username}, Rolle: {getattr(current_user.role, "name", None)})', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Granularer Rechte-Decorator

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.role:
                flash('Nicht eingeloggt oder keine Rolle!', 'danger')
                return redirect(url_for('main.index'))
            if not any(p.name == permission_name for p in current_user.role.permissions):
                flash(f'Keine Berechtigung für: {permission_name}', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Beispiel: Route für CSV-Import, geschützt durch das Recht 'import_csv'
@admin.route('/import')
@login_required
@permission_required('import_csv')
def import_csv():
    return render_template('admin/import_csv.html')

# --- Rollen & Rechte Verwaltung ---
from .models import Role, Permission

def ensure_default_permissions():
    # Standardrechte, falls noch keine existieren
    default_perms = [
        ('view_assets', 'Assets anzeigen'),
        ('edit_assets', 'Assets bearbeiten'),
        ('delete_assets', 'Assets löschen'),
        ('import_csv', 'CSV-Import'),
        ('manage_users', 'Benutzerverwaltung'),
        ('manage_roles', 'Rollenverwaltung')
    ]
    for name, desc in default_perms:
        if not Permission.query.filter_by(name=name).first():
            db.session.add(Permission(name=name, description=desc))
    db.session.commit()

@admin.route('/roles')
@login_required
@admin_required
def role_management():
    ensure_default_permissions()
    roles = Role.query.order_by(Role.id).all()
    return render_template('admin/role_management.html', roles=roles)

@admin.route('/roles/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_role():
    ensure_default_permissions()
    form = RoleForm()
    if form.validate_on_submit():
        role = Role(name=form.name.data, description=form.description.data)
        role.permissions = Permission.query.filter(Permission.id.in_(form.permissions.data)).all()
        db.session.add(role)
        db.session.commit()
        flash('Rolle erfolgreich angelegt.', 'success')
        return redirect(url_for('admin.role_management'))
    return render_template('admin/edit_role.html', form=form, role=None)

@admin.route('/roles/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_role(role_id):
    ensure_default_permissions()
    role = Role.query.get_or_404(role_id)
    form = RoleForm(obj=role)
    if request.method == 'GET':
        form.permissions.data = [p.id for p in role.permissions]
    if form.validate_on_submit():
        role.name = form.name.data
        role.description = form.description.data
        role.permissions = Permission.query.filter(Permission.id.in_(form.permissions.data)).all()
        db.session.commit()
        flash('Rolle aktualisiert.', 'success')
        return redirect(url_for('admin.role_management'))
    return render_template('admin/edit_role.html', form=form, role=role)

@admin.route('/roles/delete/<int:role_id>')
@login_required
@admin_required
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    if role.name == 'Admin':
        flash('Die Admin-Rolle kann nicht gelöscht werden.', 'danger')
        return redirect(url_for('admin.role_management'))
    db.session.delete(role)
    db.session.commit()
    flash('Rolle gelöscht.', 'success')
    return redirect(url_for('admin.role_management'))


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
        if User.query.filter_by(email=form.email.data).first():
            flash('E-Mail-Adresse bereits vergeben.', 'danger')
            return render_template('admin/add_user.html', form=form)
        from .models import Role
        user = User(
            username=form.username.data,
            role=Role.query.get(form.role.data),
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
    if request.method == 'GET':
        if user.role_id:
            form.role.data = user.role_id
    if request.method == 'POST' and form.validate_on_submit():
        user.username = form.username.data
        from .models import Role
        user.role = Role.query.get(form.role.data)
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
