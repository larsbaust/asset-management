import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Asset, Category, Location, db
from werkzeug.utils import secure_filename

import_assets = Blueprint('import_assets', __name__)

# Diese Felder stehen im System zur Verfügung
SYSTEM_FIELDS = [
    'name', 'article_number', 'serial_number', 'category', 'value', 'manufacturers', 'assignments', 'ean'
]
FIELD_LABELS = {
    'name': 'Name',
    'article_number': 'Artikelnummer',
    'serial_number': 'Seriennummer',
    'category': 'Kategorie',
    'value': 'Wert',
    'manufacturers': 'Hersteller',
    'assignments': 'Zuordnung',
    'ean': 'EAN',
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
    from app.models import Location
    headers = session.get('import_csv_headers')
    content = session.get('import_csv_content')
    if request.method != 'POST' and (not headers or not content):
        # Zeige nur das Upload-Formular (kein Mapping-UI)
        return render_template('import_assets.html')
    locations = Location.query.order_by(Location.name).all() if headers and content else []
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
        from app.models import Category
        system_categories = Category.query.order_by(Category.name).all()
        return render_template('import_assets.html', csv_headers=headers, csv_preview=preview_rows, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_templates=templates, mapping_prefill=mapping_prefill, system_categories=system_categories)
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
        locations = Location.query.order_by(Location.name).all()
        from app.models import Category
        system_categories = Category.query.order_by(Category.name).all()
        return render_template('import_assets.html', csv_headers=headers, csv_preview=preview_rows, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_templates=templates, locations=locations, system_categories=system_categories)
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
        # "Ignorieren" oder leer als None behandeln
        if not field or field.strip().lower() == '' or field.strip().lower() == 'ignorieren':
            mapping.append(None)
        else:
            mapping.append(field)
    name = request.form.get('save_template_name')
    save_mapping_template(name, mapping, headers)
    flash(f'Mapping-Vorlage "{name}" gespeichert!', 'success')
    return redirect(url_for('import_assets.import_assets_upload'))

@import_assets.route('/import/assets/mapping', methods=['POST'])
def import_assets_apply_mapping():
    headers = session.get('import_csv_headers')
    content = session.get('import_csv_content')
    location_id = request.form.get('location_id', type=int)
    print(f'[DEBUG] Gewählte location_id: {location_id}')
    print('[DEBUG] --- import_assets_apply_mapping ---')
    print('[DEBUG] Session headers:', headers)
    print('[DEBUG] Session content present:', bool(session.get('import_csv_content')), 'Länge:', len(session.get('import_csv_content')) if session.get('import_csv_content') else 0)
    if not headers or not session.get('import_csv_content'):
        print('[DEBUG] Keine CSV-Daten gefunden!')
        flash('Keine CSV-Daten gefunden. Bitte erneut hochladen.', 'danger')
        session.pop('import_csv_content', None)
        session.pop('import_csv_headers', None)
        return redirect(url_for('import_assets.import_assets_upload'))
    mapping = []
    for i, col in enumerate(headers):
        field = request.form.get(f'mapping_{i}')
        # "Ignorieren" oder leer als None behandeln
        if not field or field.strip().lower() == '' or field.strip().lower() == 'ignorieren':
            mapping.append(None)
        else:
            mapping.append(field)
    print('[DEBUG] Mapping:', mapping)

    # --- Kategorie-Mapping vorbereiten ---
    # Finde Index der gemappten Kategorie-Spalte
    try:
        category_idx = mapping.index('category')
    except ValueError:
        category_idx = None
    csv_categories = None
    from app.models import Category
    system_categories = Category.query.order_by(Category.name).all()
    if category_idx is not None:
        # Kategorien aus CSV extrahieren
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(content)
            reader = csv.reader(io.StringIO(content), dialect)
        except Exception:
            reader = csv.reader(io.StringIO(content), delimiter=';')
        next(reader, None)  # Skip header
        csv_categories = set()
        for row in reader:
            if category_idx < len(row):
                cat_val = row[category_idx].strip()
                if cat_val:
                    csv_categories.add(cat_val)
        print(f'[DEBUG] Kategorien in CSV: {csv_categories}')
        from app.models import Category
        system_categories = Category.query.order_by(Category.name).all()
    # --- Ende Kategorie-Mapping Vorbereitung ---

    # Kategorie-Mapping-Handling beim Import
    # 1. Fall: Keine Kategorie-Spalte gemappt, nutze globale Kategorie
    if request.method == 'POST' and (not csv_categories or not system_categories) and 'global_category_id' in request.form:
        global_category_id = request.form.get('global_category_id', type=int)
        if not global_category_id:
            flash('Bitte wähle eine Kategorie für alle importierten Assets!', 'danger')
            return render_template('import_assets.html', csv_headers=headers, csv_preview=None, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_prefill=mapping, locations=Location.query.order_by(Location.name).all(), system_categories=Category.query.order_by(Category.name).all())
        imported = 0
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(content)
            reader = csv.reader(io.StringIO(content), dialect)
        except Exception:
            reader = csv.reader(io.StringIO(content), delimiter=';')
        next(reader, None)  # Skip header
        for row in reader:
            asset_data = {}
            for i, field in enumerate(mapping):
                if field:
                    asset_data[field] = row[i] if i < len(row) else None
            asset = Asset(
                name=asset_data.get('name'),
                article_number=asset_data.get('article_number'),
                serial_number=asset_data.get('serial_number'),
                category_id=global_category_id,
                value=asset_data.get('value'),
                location_id=location_id if location_id else None,
                ean=asset_data.get('ean'),
            )
            db.session.add(asset)
            # Hersteller (n:m, ggf. neu anlegen)
            if 'manufacturers' in asset_data and asset_data['manufacturers']:
                from app.models import Manufacturer
                manuf_names = [n.strip() for n in asset_data['manufacturers'].replace(';', ',').split(',') if n.strip()]
                for name in manuf_names:
                    m_obj = Manufacturer.query.filter_by(name=name).first()
                    if not m_obj:
                        m_obj = Manufacturer(name=name)
                        db.session.add(m_obj)
                        db.session.flush()  # ID sofort verfügbar machen
                    if m_obj not in asset.manufacturers:
                        asset.manufacturers.append(m_obj)
            # Lieferanten (n:m)
            if 'suppliers' in asset_data and asset_data['suppliers']:
                from app.models import Supplier
                supp_names = [n.strip() for n in asset_data['suppliers'].replace(';', ',').split(',') if n.strip()]
                for name in supp_names:
                    s_obj = Supplier.query.filter_by(name=name).first()
                    if s_obj and s_obj not in asset.suppliers:
                        asset.suppliers.append(s_obj)
            # Zuordnungen (n:m, ggf. neu anlegen, Mehrfachwerte)
            if 'assignments' in asset_data and asset_data['assignments']:
                from app.models import Assignment
                assign_names = [n.strip() for n in asset_data['assignments'].replace(';', ',').split(',') if n.strip()]
                for name in assign_names:
                    a_obj = Assignment.query.filter_by(name=name).first()
                    if not a_obj:
                        a_obj = Assignment(name=name)
                        db.session.add(a_obj)
                        db.session.flush()  # ID sofort verfügbar machen
                    if a_obj not in asset.assignments:
                        asset.assignments.append(a_obj)
            imported += 1
        db.session.commit()
        flash(f'{imported} Assets importiert!', 'success')
        session.pop('import_csv_content', None)
        session.pop('import_csv_headers', None)
        return redirect(url_for('import_assets.import_assets_upload'))

    # 2. Fall: Kategorie-Mapping wie bisher (pro CSV-Kategorie)
    if request.method == 'POST' and csv_categories and system_categories:
        # Kategorie-Mapping aus dem Formular lesen
        category_mapping = {}
        assignment_mapping = {}
        from app.models import Assignment
        for csv_cat in csv_categories:
            mapped_id = request.form.get(f'category_mapping_{csv_cat}')
            if not mapped_id:
                flash(f'Für die CSV-Kategorie "{csv_cat}" wurde keine System-Kategorie ausgewählt!', 'danger')
                return render_template('import_assets.html', csv_headers=headers, csv_preview=None, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_prefill=mapping, locations=Location.query.order_by(Location.name).all(), csv_categories=csv_categories, system_categories=system_categories)
            category_mapping[csv_cat] = int(mapped_id)
            # Assignment-Mapping (Dropdown oder Freitext)
            assignment_id = request.form.get(f'assignment_mapping_{csv_cat}')
            assignment_new = request.form.get(f'assignment_mapping_new_{csv_cat}')
            if assignment_new:
                a_obj = Assignment.query.filter_by(name=assignment_new).first()
                if not a_obj:
                    a_obj = Assignment(name=assignment_new)
                    db.session.add(a_obj)
                    db.session.flush()
                assignment_mapping[csv_cat] = a_obj
            elif assignment_id:
                a_obj = Assignment.query.filter_by(id=assignment_id).first()
                if a_obj:
                    assignment_mapping[csv_cat] = a_obj
        print(f'[DEBUG] Kategorie-Mapping: {category_mapping}')
        print(f'[DEBUG] Assignment-Mapping: {assignment_mapping}')

        # Importiere Assets mit Mapping
        imported = 0
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(content)
            reader = csv.reader(io.StringIO(content), dialect)
        except Exception:
            reader = csv.reader(io.StringIO(content), delimiter=';')
        next(reader, None)  # Skip header
        for row in reader:
            asset_data = {}
            for i, field in enumerate(mapping):
                if field:
                    asset_data[field] = row[i] if i < len(row) else None
            # Kategorie-Mapping anwenden
            csv_cat_val = row[category_idx].strip() if category_idx < len(row) else None
            cat_id = category_mapping.get(csv_cat_val)
            if not cat_id:
                flash(f'Keine System-Kategorie für CSV-Kategorie "{csv_cat_val}" zugeordnet!', 'danger')
                return render_template('import_assets.html', csv_headers=headers, csv_preview=None, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_prefill=mapping, locations=Location.query.order_by(Location.name).all(), csv_categories=csv_categories, system_categories=system_categories)
            asset = Asset(
                name=asset_data.get('name'),
                article_number=asset_data.get('article_number'),
                serial_number=asset_data.get('serial_number'),
                category_id=cat_id,
                value=asset_data.get('value'),
                location_id=location_id if location_id else None,
            )
            # Kategorie→Zuordnung-Mapping anwenden
            csv_cat_val = row[category_idx].strip() if category_idx < len(row) else None
            if csv_cat_val and csv_cat_val in assignment_mapping:
                a_obj = assignment_mapping[csv_cat_val]
                if a_obj and a_obj not in asset.assignments:
                    asset.assignments.append(a_obj)

            db.session.add(asset)
            imported += 1
        db.session.commit()
        flash(f'{imported} Assets importiert!', 'success')
        session.pop('import_csv_content', None)
        session.pop('import_csv_headers', None)
        return redirect(url_for('import_assets.import_assets_upload'))

    # Übergabe an Template
    return render_template('import_assets.html', csv_headers=headers, csv_preview=None, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_prefill=mapping, locations=Location.query.order_by(Location.name).all(), csv_categories=csv_categories, system_categories=system_categories)

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
    # Prüfe, ob das Pflichtfeld 'Name' zugeordnet ist (und nicht ignoriert wurde)
    print('[DEBUG] Mapping für Pflichtfeld-Prüfung:', mapping)
    name_assigned = False
    for idx, field in enumerate(mapping):
        print(f'[DEBUG] Mapping[{idx}]:', repr(field))
        if field and str(field).strip().lower() == 'name':
            name_assigned = True
            print(f'[DEBUG] -> Pflichtfeld "Name" zugeordnet an Spalte {idx}')
            break
    if not name_assigned:
        print('[DEBUG] -> Pflichtfeld "Name" NICHT zugeordnet!')
        flash("Pflichtfeld 'Name' wurde im Mapping nicht zugeordnet. Import abgebrochen.", 'danger')
        session.pop('import_csv_content', None)
        session.pop('import_csv_headers', None)
        return redirect(url_for('import_assets.import_assets_upload'))
    for row_num, row in enumerate(reader, start=2):
        asset_data = {}
        for idx, field in enumerate(mapping):
            # Leere Felder oder "Ignorieren" (case-insensitive) überspringen
            if not field or str(field).strip().lower() == 'ignorieren':
                continue  # Ignorieren
            if idx >= len(row):
                flash(f"Zu wenig Spalten in Zeile {row_num}. Import abgebrochen.", 'danger')
                session.pop('import_csv_content', None)
                session.pop('import_csv_headers', None)
                return redirect(url_for('import_assets.import_assets_upload'))
            asset_data[field] = row[idx]
        # Pflichtfeld-Prüfung
        if not asset_data.get('name'):
            flash(f"Pflichtfeld 'Name' fehlt in Zeile {row_num}. Import abgebrochen.", 'danger')
            session.pop('import_csv_content', None)
            session.pop('import_csv_headers', None)
            return redirect(url_for('import_assets.import_assets_upload'))
        # Kategorie zuordnen (und ggf. automatisch anlegen)
        cat_id = None
        if 'category' in asset_data and asset_data['category']:
            cat = Category.query.filter_by(name=asset_data['category']).first()
            if not cat:
                cat = Category(name=asset_data['category'])
                db.session.add(cat)
                db.session.commit()
            cat_id = cat.id
        else:
            flash(f"Kategorie fehlt oder leer in Zeile {row_num}. Import abgebrochen.", 'danger')
            session.pop('import_csv_content', None)
            session.pop('import_csv_headers', None)
            return redirect(url_for('import_assets.import_assets_upload'))

        asset = Asset(
            name=asset_data.get('name'),
            article_number=asset_data.get('article_number'),
            serial_number=asset_data.get('serial_number'),
            category_id=cat_id,
            value=asset_data.get('value'),
            location_id=location_id if location_id else None,
        )
        db.session.add(asset)
        imported += 1
    db.session.commit()
    flash(f'{imported} Assets importiert!', 'success')
    session.pop('import_csv_content', None)
    session.pop('import_csv_headers', None)
    return redirect(url_for('import_assets.import_assets_upload'))
