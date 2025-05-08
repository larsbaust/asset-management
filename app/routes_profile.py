from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .models import db, User
from .forms import ProfileForm
import os
from werkzeug.utils import secure_filename

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

@profile_bp.route('/', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(current_user.id)
    form = ProfileForm(obj=user)
    if request.method == 'POST' and form.validate_on_submit():
        # Nur Profilfelder aktualisieren
        user.vorname = form.vorname.data
        user.nachname = form.nachname.data
        user.email = form.email.data
        user.street = form.street.data
        user.postal_code = form.postal_code.data
        user.city = form.city.data
        user.phone = form.phone.data

        # Bild löschen-Flag prüfen
        delete_image_flag = request.form.get('delete_image_flag')
        if delete_image_flag == '1':
            # Altes Bild löschen, falls vorhanden
            if user.profile_image and user.profile_image != '' and os.path.exists(os.path.join('static/profile_images', user.profile_image)):
                try:
                    os.remove(os.path.join('static/profile_images', user.profile_image))
                except Exception:
                    pass
            user.profile_image = ''
        else:
            cropped_image_data = request.form.get('cropped_image_data')
            if cropped_image_data and cropped_image_data.startswith('data:image/png;base64,'):
                import base64
                from datetime import datetime
                img_data = base64.b64decode(cropped_image_data.split(',')[1])
                filename = f"{user.username}_profile_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                img_path = os.path.join('static/profile_images', filename)
                os.makedirs(os.path.dirname(img_path), exist_ok=True)
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                # Altes Bild löschen, falls vorhanden und nicht Default
                if user.profile_image and user.profile_image != '' and os.path.exists(os.path.join('static/profile_images', user.profile_image)):
                    try:
                        os.remove(os.path.join('static/profile_images', user.profile_image))
                    except Exception:
                        pass
                user.profile_image = filename
            elif form.profile_image.data:
                filename = secure_filename(form.profile_image.data.filename)
                img_path = os.path.join('static/profile_images', filename)
                os.makedirs(os.path.dirname(img_path), exist_ok=True)
                form.profile_image.data.save(img_path)
                user.profile_image = filename
        db.session.commit()
        flash('Profil erfolgreich aktualisiert.', 'success')
        # User-Objekt neu laden, damit Ansicht die aktuellen Werte zeigt
        return redirect(url_for('profile.profile'))

    # Bild existiert wirklich?
    image_exists = False
    if user.profile_image:
        img_path = os.path.join('static/profile_images', user.profile_image)
        image_exists = os.path.exists(img_path)
    # Avatar-Name robust bestimmen
    if user.vorname or user.nachname:
        avatar_name = f"{user.vorname or ''} {user.nachname or ''}".strip()
    else:
        avatar_name = user.username or "User"
    return render_template('profile/profile.html', form=form, user=user, image_exists=image_exists, avatar_name=avatar_name)
