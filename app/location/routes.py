from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from flask_wtf.csrf import validate_csrf, ValidationError
from app.location import location
from app import db
from app.models import Location
from app.location.location_utils import import_locations_from_csv
from app.admin import permission_required
from werkzeug.utils import secure_filename
import os

@location.route('/import', methods=['GET', 'POST'])
@login_required
@permission_required('import_locations')
def import_locations():
    """Standorte aus CSV-Datei importieren"""
    if request.method == 'POST':
        # Prüfen ob Datei vorhanden ist
        if 'csv_file' not in request.files:
            flash('Keine Datei ausgewählt', 'danger')
            return redirect(request.url)
        
        file = request.files['csv_file']
        
        # Prüfen ob Dateiname vorhanden
        if file.filename == '':
            flash('Keine Datei ausgewählt', 'danger')
            return redirect(request.url)
            
        # Prüfen ob es sich um eine CSV handelt
        if file and file.filename.endswith('.csv'):
            delimiter = request.form.get('delimiter', ',')
            
            # Import durchführen
            result = import_locations_from_csv(file, delimiter)
            
            # Feedback an Benutzer
            if result['imported'] > 0:
                flash(f"{result['imported']} Standorte erfolgreich importiert", 'success')
            
            if result['skipped'] > 0:
                flash(f"{result['skipped']} Standorte übersprungen", 'warning')
                
            if result['errors']:
                for error in result['errors'][:5]:  # Nur die ersten 5 Fehler anzeigen
                    flash(error, 'danger')
                    
                if len(result['errors']) > 5:
                    flash(f"... und {len(result['errors']) - 5} weitere Fehler", 'danger')
            
            return redirect(url_for('main.locations'))
        else:
            flash('Bitte eine CSV-Datei auswählen', 'danger')
            
    return render_template('location/import.html')

@location.route('/new', methods=['POST'])
@login_required
def new_location():
    """Neuen Standort erstellen (für MD3 UI)"""
    try:
        # CSRF Token validieren
        try:
            validate_csrf(request.form.get('csrf_token'))
        except ValidationError:
            return jsonify({'success': False, 'error': 'CSRF-Token ungültig'}), 400
        
        # Daten aus dem Request extrahieren
        name = request.form.get('name', '').strip()
        street = request.form.get('street', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        postal_code = request.form.get('zip_code', '').strip()  # zip_code -> postal_code
        country = request.form.get('country', '').strip()
        description = request.form.get('description', '').strip()
        
        # Validierung
        if not name:
            return jsonify({'success': False, 'error': 'Name ist erforderlich'}), 400
        
        # Prüfen ob Standort bereits existiert
        existing = Location.query.filter_by(name=name).first()
        if existing:
            return jsonify({'success': False, 'error': f'Standort "{name}" existiert bereits'}), 400
        
        # Neuen Standort erstellen
        location_obj = Location(
            name=name,
            street=street,
            city=city,
            state=state,
            postal_code=postal_code,
            description=description if description else None
        )
        
        db.session.add(location_obj)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Standort "{name}" erfolgreich erstellt',
            'location': {
                'id': location_obj.id,
                'name': location_obj.name,
                'street': location_obj.street,
                'city': location_obj.city,
                'state': location_obj.state,
                'postal_code': location_obj.postal_code,
                'description': location_obj.description
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Fehler beim Erstellen: {str(e)}'}), 500
