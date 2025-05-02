import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Asset, Category, db
from werkzeug.utils import secure_filename

import_assets = Blueprint('import_assets', __name__)

# Diese Felder stehen im System zur Verfügung
SYSTEM_FIELDS = [
    'name', 'article_number', 'serial_number', 'category', 'value', 'manufacturers', 'assignments'
]
FIELD_LABELS = {
    'name': 'Name',
    'article_number': 'Artikelnummer',
    'serial_number': 'Seriennummer',
    'category': 'Kategorie',
    'value': 'Wert',
    'manufacturers': 'Hersteller',
    'assignments': 'Zuordnung',
}

import os
import json

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'import_mapping_templates')
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# Hilfsfunktionen

def save_mapping_template(name, mapping, headers):
    tpl = {
        'name': name,
        'mapping': mapping,
        'headers': headers
    }
    with open(os.path.join(TEMPLATE_DIR, f'{name}.json'), 'w', encoding='utf-8') as f:
        json.dump(tpl, f)

def load_mapping_template(name):
    path = os.path.join(TEMPLATE_DIR, f'{name}.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def list_mapping_templates():
    return [f[:-5] for f in os.listdir(TEMPLATE_DIR) if f.endswith('.json')]

@import_assets.route('/import/assets', methods=['GET', 'POST'])
def import_assets_upload():
    print('[DEBUG] --- import_assets_upload ---')
    print('[DEBUG] Request method:', request.method)
    # Mapping-Vorlage laden
    if request.method == 'POST' and 'load_template' in request.form:
        template_name = request.form.get('template_name')
        headers = session.get('import_csv_headers')
        content = session.get('import_csv_content')
        templates = list_mapping_templates()
        mapping_template = load_mapping_template(template_name)
        mapping_prefill = mapping_template['mapping'] if mapping_template else []
        preview_rows = []
        if content and headers:
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(content)
                reader = csv.reader(io.StringIO(content), dialect)
            except Exception:
                reader = csv.reader(io.StringIO(content), delimiter=';')
            next(reader, None)
            for _ in range(5):
                try:
                    preview_rows.append(next(reader))
                except StopIteration:
                    break
        return render_template('import_assets.html', csv_headers=headers, csv_preview=preview_rows, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_templates=templates, mapping_prefill=mapping_prefill)
    # Standard-Upload-Flow
    if request.method == 'POST' and 'csvfile' in request.files:
        file = request.files['csvfile']
        if not file.filename.endswith('.csv'):
            flash('Nur CSV-Dateien sind erlaubt.', 'danger')
            return redirect(url_for('import_assets.import_assets_upload'))
        content = file.read().decode('utf-8')
        # Trennzeichen automatisch erkennen, Fallback auf ;
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(content)
            reader = csv.reader(io.StringIO(content), dialect)
        except Exception:
            reader = csv.reader(io.StringIO(content), delimiter=';')
        headers = next(reader)
        flash(f"Erkannte CSV-Header: {headers}", 'info')
        print(f"[DEBUG] Erkannte CSV-Header: {headers}")
        # Vorschau: Die nächsten 5 Zeilen lesen
        preview_rows = []
        for _ in range(5):
            try:
                preview_rows.append(next(reader))
            except StopIteration:
                break
        session['import_csv_headers'] = headers
        session['import_csv_content'] = content
        templates = list_mapping_templates()
        return render_template('import_assets.html', csv_headers=headers, csv_preview=preview_rows, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_templates=templates)
    else:
        flash('Ungültige Datei. Bitte eine CSV-Datei wählen.', 'danger')
        return redirect(url_for('import_assets.import_assets_upload'))

# Endpunkt zum Speichern einer Mapping-Vorlage
@import_assets.route('/import/assets/save_mapping_template', methods=['POST'])
def save_mapping_template_route():
    headers = session.get('import_csv_headers')
    mapping = []
    for i, col in enumerate(headers):
        field = request.form.get(f'mapping_{i}')
        mapping.append(field)
    name = request.form.get('save_template_name')
    save_mapping_template(name, mapping, headers)
    flash(f'Mapping-Vorlage "{name}" gespeichert!', 'success')
    return redirect(url_for('import_assets.import_assets_upload'))

@import_assets.route('/import/assets/mapping', methods=['POST'])
def import_assets_apply_mapping():
    headers = session.get('import_csv_headers')
    print('[DEBUG] --- import_assets_apply_mapping ---')
    print('[DEBUG] Session headers:', headers)
    print('[DEBUG] Session content present:', bool(session.get('import_csv_content')), 'Länge:', len(session.get('import_csv_content')) if session.get('import_csv_content') else 0)
    if not headers or not session.get('import_csv_content'):
        print('[DEBUG] Keine CSV-Daten gefunden!')
        flash('Keine CSV-Daten gefunden. Bitte erneut hochladen.', 'danger')
        return redirect(url_for('import_assets.import_assets_upload'))
    mapping = []
    for i, col in enumerate(headers):
        field = request.form.get(f'mapping_{i}')
        mapping.append(field)
    print('[DEBUG] Mapping:', mapping)
    # Trennzeichen automatisch erkennen, Fallback auf ;
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(content)
        print('[DEBUG] CSV-Dialekt erkannt:', dialect.delimiter)
        reader = csv.reader(io.StringIO(content), dialect)
    except Exception as e:
        print('[DEBUG] Fehler bei CSV.Sniffer:', e)
        reader = csv.reader(io.StringIO(content), delimiter=';')
    try:
        next(reader)  # Skip header
    except Exception as e:
        print('[DEBUG] Fehler beim Überspringen des Headers:', e)
    imported = 0
    imported = 0
    if 'name' not in mapping:
        flash("Pflichtfeld 'Name' wurde im Mapping nicht zugeordnet. Import abgebrochen.", 'danger')
        return redirect(url_for('import_assets.import_assets_upload'))
    for row_num, row in enumerate(reader, start=2):
        asset_data = {}
        for idx, field in enumerate(mapping):
            if not field:
                continue  # Ignorieren
            asset_data[field] = row[idx]
        # Pflichtfeld-Prüfung
        if not asset_data.get('name'):
            flash(f"Pflichtfeld 'Name' fehlt in Zeile {row_num}. Import abgebrochen.", 'danger')
            return redirect(url_for('import_assets.import_assets_upload'))
        # Kategorie zuordnen (Beispiel für ForeignKey)
        if 'category' in asset_data:
            cat = Category.query.filter_by(name=asset_data['category']).first()
            if cat:
                asset_data['category'] = cat
            else:
                asset_data['category'] = None
        asset = Asset(
            name=asset_data.get('name'),
            article_number=asset_data.get('article_number'),
            serial_number=asset_data.get('serial_number'),
            category=asset_data.get('category'),
            value=asset_data.get('value'),
        )
        db.session.add(asset)
        imported += 1
    db.session.commit()
    flash(f'{imported} Assets importiert!', 'success')
    session.pop('import_csv_content', None)
    session.pop('import_csv_headers', None)
    return redirect(url_for('import_assets.import_assets_upload'))
