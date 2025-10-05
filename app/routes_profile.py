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
    user = User.query.get(current_user.id)
    form = ProfileForm(obj=user)
    
    # Debug: POST-Daten anzeigen
    if request.method == 'POST':
        print("=== POST REQUEST ===")
        print(f"Form validate: {form.validate_on_submit()}")
        print(f"Form errors: {form.errors}")
        print(f"cropped_image_data vorhanden: {'cropped_image_data' in request.form}")
        print(f"delete_image_flag: {request.form.get('delete_image_flag')}")
        if 'cropped_image_data' in request.form:
            cropped_data = request.form.get('cropped_image_data')
            print(f"cropped_image_data Länge: {len(cropped_data) if cropped_data else 0}")
            print(f"cropped_image_data startet mit data:image: {cropped_data.startswith('data:image') if cropped_data else False}")
    
    if request.method == 'POST':
        # Nur Profilfelder aktualisieren (direkt aus request.form lesen)
        user.vorname = request.form.get('vorname') or user.vorname
        user.nachname = request.form.get('nachname') or user.nachname
        user.email = request.form.get('email') or user.email
        user.street = request.form.get('street') or user.street
        user.postal_code = request.form.get('postal_code') or user.postal_code
        user.city = request.form.get('city') or user.city
        user.phone = request.form.get('phone') or user.phone

        # Bild löschen-Flag prüfen
        delete_image_flag = request.form.get('delete_image_flag')
        static_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'profile_images')
        
        if delete_image_flag == '1':
            # Altes Bild löschen, falls vorhanden
            if user.profile_image and user.profile_image != '':
                old_img_path = os.path.join(static_root, user.profile_image)
                if os.path.exists(old_img_path):
                    try:
                        os.remove(old_img_path)
                        print(f"Altes Bild gelöscht: {old_img_path}")
                    except Exception as e:
                        print(f"Fehler beim Löschen: {e}")
            user.profile_image = ''
        else:
            cropped_image_data = request.form.get('cropped_image_data')
            if cropped_image_data and cropped_image_data.startswith('data:image/png;base64,'):
                import base64
                from datetime import datetime
                img_data = base64.b64decode(cropped_image_data.split(',')[1])
                filename = f"{user.username}_profile_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                img_path = os.path.join(static_root, filename)
                os.makedirs(static_root, exist_ok=True)
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                print(f'Profilbild gespeichert: {img_path}')
                print(f'Datei existiert nach dem Speichern: {os.path.exists(img_path)}')
                
                # Altes Bild nur löschen, wenn es nicht das neue ist
                if user.profile_image and user.profile_image != filename:
                    old_img_path = os.path.join(static_root, user.profile_image)
                    if os.path.exists(old_img_path):
                        try:
                            os.remove(old_img_path)
                            print(f'Altes Bild gelöscht: {old_img_path}')
                        except Exception as e:
                            print(f'Fehler beim Löschen des alten Bildes: {e}')
                
                user.profile_image = filename
                print(f'user.profile_image gesetzt auf: {user.profile_image}')
            # Die Verarbeitung des Profilbilds erfolgt ausschließlich über das Modal
            # und wird bereits über cropped_image_data oben behandelt
        try:
            db.session.commit()
            flash('Profil erfolgreich aktualisiert.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern: {str(e)}', 'error')
            print(f"Fehler beim Speichern des Profils: {e}")
        
        # User-Objekt neu laden, damit Ansicht die aktuellen Werte zeigt
        return redirect(url_for('profile.profile'))

    # Bild existiert wirklich?
    image_exists = False
    if user.profile_image:
        # Absoluter Pfad zum Bild (konsistent mit Speicher-Logik)
        static_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'profile_images')
        img_path = os.path.join(static_root, user.profile_image)
        image_exists = os.path.exists(img_path)
        print(f"Prüfe Bild: {img_path} -> Existiert: {image_exists}")
        if not image_exists:
            print(f"Bild nicht gefunden, setze profile_image auf leer")
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
    return render_template('md3/profile/profile.html', form=form, user=user, image_exists=image_exists, avatar_name=avatar_name, cache_buster=cache_buster)
