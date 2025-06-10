from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
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
