from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.suppliers import suppliers
from app.models import Supplier
from app import db
from app.suppliers.supplier_utils import import_suppliers_from_csv
from app.admin import permission_required
from werkzeug.utils import secure_filename
import os

@suppliers.route('/suppliers')
def supplier_list():
    query = Supplier.query
    search = request.args.get('search', '')
    letter = request.args.get('letter', '')
    if search:
        query = query.filter(Supplier.name.ilike(f"%{search}%"))
    if letter and letter != "Alle":
        query = query.filter(Supplier.name.ilike(f"{letter}%"))
    suppliers_list = query.order_by(Supplier.name).all()
    return render_template('suppliers/list.html', suppliers=suppliers_list, search=search, letter=letter)

@suppliers.route('/suppliers/add')
def supplier_add():
    return "Hier kommt das Formular zum Anlegen eines Lieferanten."

@suppliers.route('/suppliers/import', methods=['GET', 'POST'])
@login_required
@permission_required('import_suppliers')
def import_suppliers():
    """Lieferanten aus CSV-Datei importieren"""
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
            result = import_suppliers_from_csv(file, delimiter)
            
            # Feedback an Benutzer
            if result['imported'] > 0:
                flash(f"{result['imported']} Lieferanten erfolgreich importiert", 'success')
            
            if result['skipped'] > 0:
                flash(f"{result['skipped']} Lieferanten übersprungen", 'warning')
                
            if result['errors']:
                for error in result['errors'][:5]:  # Nur die ersten 5 Fehler anzeigen
                    flash(error, 'danger')
                    
                if len(result['errors']) > 5:
                    flash(f"... und {len(result['errors']) - 5} weitere Fehler", 'danger')
            
            return redirect(url_for('suppliers.supplier_list'))
        else:
            flash('Bitte eine CSV-Datei auswählen', 'danger')
            
    from datetime import datetime
    return render_template('suppliers/import.html', now=datetime.now())
