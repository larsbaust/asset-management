from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from .models import db, User
from .forms import ProfileForm
import os
print('--- FLASK STARTUP DEBUG ---')
print('Aktuelles Arbeitsverzeichnis:', os.getcwd())
print('Erwarteter Static-Pfad:', os.path.abspath(os.path.join(os.getcwd(), 'static')))
print('----------------------------')

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

@profile_bp.route('/', methods=['GET', 'POST'])
@login_required
def profile():
    md3 = request.values.get('md3', type=int)
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
                # Profilbild immer im Projekt-Root-static/profile_images speichern
                static_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'profile_images')
                img_path = os.path.join(static_root, filename)
                os.makedirs(os.path.dirname(img_path), exist_ok=True)
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                print('Profilbild gespeichert:', img_path)
                print('Datei existiert nach dem Speichern:', os.path.exists(img_path))
                # Altes Bild nur löschen, wenn es nicht das neue ist
                if user.profile_image and user.profile_image != filename and os.path.exists(os.path.join('static/profile_images', user.profile_image)):
                    try:
                        os.remove(os.path.join('static/profile_images', user.profile_image))
                    except Exception:
                        pass
                user.profile_image = filename
            # Die Verarbeitung des Profilbilds erfolgt ausschließlich über das Modal
            # und wird bereits über cropped_image_data oben behandelt
        db.session.commit()
        flash('Profil erfolgreich aktualisiert.', 'success')
        # User-Objekt neu laden, damit Ansicht die aktuellen Werte zeigt
        redirect_params = {'md3': 1} if md3 else {}
        return redirect(url_for('profile.profile', **redirect_params))

    # Bild existiert wirklich?
    image_exists = False
    if user.profile_image:
        img_path = os.path.join('static/profile_images', user.profile_image)
        image_exists = os.path.exists(img_path)
        if not image_exists:
            user.profile_image = ''
            db.session.commit()
            image_exists = False
    # Avatar-Name robust bestimmen
    if user.vorname or user.nachname:
        avatar_name = f"{user.vorname or ''} {user.nachname or ''}".strip()
    else:
        avatar_name = user.username if user.username else "User"
    from random import randint
    cache_buster = randint(0, 1000000)
    if md3:
        return render_template('md3/profile/profile.html', form=form, user=user, image_exists=image_exists, avatar_name=avatar_name, cache_buster=cache_buster)
    return render_template('profile/profile.html', form=form, user=user, image_exists=image_exists, avatar_name=avatar_name, cache_buster=cache_buster)
