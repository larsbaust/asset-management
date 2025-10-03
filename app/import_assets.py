import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Asset, Category, Location, db
from werkzeug.utils import secure_filename

import_assets = Blueprint('import_assets', __name__)

# Diese Felder stehen im System zur Verfügung
SYSTEM_FIELDS = [
    'name', 'article_number', 'serial_number', 'category', 'value', 'manufacturers', 'assignments', 'ean', 'quantity'
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
    'quantity': 'Anzahl (quantity/Menge/Stück)'
}

import os
import json

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'import_mapping_templates')
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# Hilfsfunktionen

def safe_name(name):
    import re
    return re.sub(r'[^a-zA-Z0-9_]', '_', str(name))

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
    md3 = request.values.get('md3', type=int)
    headers = session.get('import_csv_headers')
    content = session.get('import_csv_content')
    from app.models import Supplier
    initial_suppliers = Supplier.query.order_by(Supplier.name).all()

    template_name = 'md3/assets/import_assets.html' if md3 else 'import_assets.html'

    def render_import_template(**context):
        context.setdefault('md3', md3)
        return render_template(template_name, **context)

    if request.method != 'POST' and (not headers or not content):
        # Zeige nur das Upload-Formular (kein Mapping-UI)
        return render_import_template(suppliers=initial_suppliers)

    locations = Location.query.order_by(Location.name).all() if headers and content else []
    from app.models import Supplier
    suppliers = Supplier.query.order_by(Supplier.name).all() if headers and content else []
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
        safe_csv_categories = {col: safe_name(col) for col in headers}
        return render_import_template(csv_headers=headers, csv_preview=preview_rows, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_templates=templates, mapping_prefill=mapping_prefill, system_categories=system_categories, safe_csv_categories=safe_csv_categories, suppliers=suppliers, locations=locations)
    # Standard-Upload-Flow
    if request.method == 'POST' and 'csvfile' in request.files:
        file = request.files['csvfile']
        if not file.filename.endswith('.csv'):
            flash('Nur CSV-Dateien sind erlaubt.', 'danger')
            return redirect(url_for('import_assets.import_assets_upload', md3=1 if md3 else None))
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
        safe_csv_categories = {col: safe_name(col) for col in headers}
        return render_import_template(csv_headers=headers, csv_preview=preview_rows, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_templates=templates, locations=locations, system_categories=system_categories, safe_csv_categories=safe_csv_categories, suppliers=suppliers)
    else:
        flash('Ungültige Datei. Bitte eine CSV-Datei wählen.', 'danger')
        return redirect(url_for('import_assets.import_assets_upload', md3=1 if md3 else None))

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
    return redirect(url_for('import_assets.import_assets_upload', md3=1 if request.values.get('md3', type=int) else None))

@import_assets.route('/import/assets/mapping', methods=['POST'])
def import_assets_apply_mapping():
    print('[DEBUG] Start import_assets_apply_mapping')
    from app.models import Category, Assignment
    print('[DEBUG] Form-Inhalt:', dict(request.form))
    headers = session.get('import_csv_headers')
    content = session.get('import_csv_content')
    location_id = request.form.get('location_id', type=int)
    supplier_id = request.form.get('global_supplier_id', type=int)
    print(f'[DEBUG] Gewählte location_id: {location_id}')
    print(f'[DEBUG] Gewählte supplier_id: {supplier_id}')
    print('[DEBUG] --- import_assets_apply_mapping ---')
    print('[DEBUG] Session headers:', headers)
    print('[DEBUG] Session content present:', bool(session.get('import_csv_content')), 'Länge:', len(session.get('import_csv_content')) if session.get('import_csv_content') else 0)
    if not headers or not session.get('import_csv_content'):
        print('[DEBUG] Abbruch: Keine CSV-Daten gefunden!')
        flash('Keine CSV-Daten gefunden. Bitte erneut hochladen.', 'danger')
        session.pop('import_csv_content', None)
        session.pop('import_csv_headers', None)
        return redirect(url_for('import_assets.import_assets_upload'))
    mapping = []
    for col in headers:
        field = request.form.get(f'category_mapping_{col}')
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
    # System-Kategorie-Zuordnung und Mapping werden nicht mehr benötigt!
    # Import funktioniert jetzt mit global_category_id ODER mit CSV-Mapping auf 'Kategorie'.
    global_category_id = request.form.get('global_category_id', type=int)
    # Die weiteren Prüfungen und Mappings für System-Kategorien und Assignments wurden entfernt.
    # Pflichtfeldprüfung: Mindestens ein Feld muss auf 'name' gemappt sein
    name_mapped = 'name' in mapping
    print(f'[DEBUG] Name-Mapping-Pflichtfeldprüfung: {mapping}')
    if not name_mapped:
        print('[DEBUG] Kein Name-Feld zugeordnet, zurück zum UI!')
        flash('Mindestens eine CSV-Spalte muss dem Feld "Name" zugeordnet werden!', 'danger')
        # Erzeuge safe_csv_categories für alle Spalten
        safe_csv_categories = {col: col.replace(' ', '_').replace('-', '_').replace('.', '_').lower() for col in headers}
        return render_import_template(csv_headers=headers, csv_preview=None, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_prefill=mapping, locations=Location.query.order_by(Location.name).all(), safe_csv_categories=safe_csv_categories)

    # Importiere Assets mit Mapping
    category_mapping = {}
    assignment_mapping = {}
    imported = 0
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
    global_category_id = request.form.get('global_category_id', type=int)
    print('[DEBUG] Vor rows = list(reader)')
    rows = list(reader)
    print('[DEBUG] Nach rows = list(reader)')
    print(f'[DEBUG] Zeilen im CSV-Reader nach Header-Skip: {len(rows)}')
    for i, row in enumerate(rows):
        print(f'[DEBUG] Zeile {i}: {row}')
    # Prüfe, ob ein "quantity"-Feld gemappt ist
    quantity_idx = None
    if 'quantity' in mapping:
        quantity_idx = mapping.index('quantity')
    price_total_idx = None
    if 'priceTotal' in mapping:
        price_total_idx = mapping.index('priceTotal')
    price_idx = None
    if 'value' in mapping:
        price_idx = mapping.index('value')
    for row_num, row in enumerate(rows, start=2):
        print(f'[DEBUG] Importiere Zeile {row_num}: {row}')
        asset_data = {}
        for i, field in enumerate(mapping):
            if field:
                asset_data[field] = row[i] if i < len(row) else None
        # Kategorie-Mapping anwenden
        csv_cat_val = None
        if category_idx is not None:
            csv_cat_val = row[category_idx].strip() if category_idx < len(row) else None
            if csv_cat_val:
                from app.models import Category
                category = Category.query.filter_by(name=csv_cat_val).first()
                if not category:
                    category = Category(name=csv_cat_val)
                    db.session.add(category)
                    db.session.flush()  # ID sofort verfügbar
                cat_id = category.id
            else:
                cat_id = None
        else:
            cat_id = global_category_id
        if not cat_id:
            flash(f'Keine System-Kategorie für CSV-Kategorie "{csv_cat_val}" zugeordnet!', 'danger')
            print('[DEBUG] Fehler-Return: Keine System-Kategorie zugeordnet')
            safe_csv_categories = {col: safe_name(col) for col in headers}
            from app.models import Category
            system_categories = Category.query.order_by(Category.name).all()
            return render_import_template(csv_headers=headers, csv_preview=None, system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS, mapping_prefill=mapping, locations=Location.query.order_by(Location.name).all(), system_categories=system_categories, safe_csv_categories=safe_csv_categories)
        # Anzahl bestimmen
        try:
            qty = int(row[quantity_idx]) if quantity_idx is not None and row[quantity_idx] else 1
            if qty < 1:
                qty = 1
        except Exception:
            qty = 1
        # Einzelpreis berechnen, falls nötig
        einzelpreis = None
        if (asset_data.get('value') is None or asset_data.get('value') == '') and price_total_idx is not None and quantity_idx is not None:
            try:
                price_total_val = row[price_total_idx]
                qty_val = row[quantity_idx]
                if price_total_val and qty_val:
                    einzelpreis = round(float(price_total_val) / int(qty_val), 2)
            except Exception as e:
                einzelpreis = None
        for _ in range(qty):
            # Sicherstellen, dass jedes Asset einen Namen hat - verwende Artikelnummer oder generiere Standardnamen
            asset_name = asset_data.get('name')
            if not asset_name or asset_name.strip() == '':
                # Verwende Artikelnummer als Fallback, wenn vorhanden
                if asset_data.get('article_number') and asset_data.get('article_number').strip() != '':
                    asset_name = f"Asset {asset_data.get('article_number')}"
                # Wenn weder Name noch Artikelnummer vorhanden sind, generiere einen Standardnamen mit Zeilennummer
                else:
                    asset_name = f"Importiertes Asset #{row_num}"
                print(f'[DEBUG] Asset ohne Namen in Zeile {row_num}: Verwende Standardnamen "{asset_name}"')
                
            asset = Asset(
                name=asset_name,
                article_number=asset_data.get('article_number'),
                serial_number=asset_data.get('serial_number'),
                category_id=cat_id,
                value=asset_data.get('value') if asset_data.get('value') not in (None, '') else einzelpreis,
                location_id=location_id if location_id else None,
                ean=asset_data.get('ean'),
            )
            # Fallback-Hinweis, falls kein Preis berechnet werden konnte
            if (asset_data.get('value') in (None, '')) and price_total_idx is not None and einzelpreis is None:
                flash(f"Hinweis: Für Asset '{asset_data.get('name')}' konnte kein Einzelpreis aus 'priceTotal' berechnet werden.", 'warning')
            # Hersteller-Zuordnung (Mehrfach möglich, Komma-getrennt)
            manufacturers_value = asset_data.get('manufacturers')
            if manufacturers_value:
                names = [n.strip() for n in manufacturers_value.split(',')]
                print(f'[DEBUG] Hersteller-Zuordnung für Asset: {asset.name}: {names}')
                from app.models import Manufacturer
                for name in names:
                    if not name:
                        continue
                    manufacturer = Manufacturer.query.filter_by(name=name).first()
                    if not manufacturer:
                        manufacturer = Manufacturer(name=name)
                        db.session.add(manufacturer)
                        db.session.flush()  # ID sofort verfügbar
                    if manufacturer not in asset.manufacturers:
                        asset.manufacturers.append(manufacturer)
            # Zuordnung (Assignments) aus CSV übernehmen
            assignments_value = asset_data.get('assignments')
            if assignments_value:
                assignment_names = [n.strip() for n in assignments_value.split(',')]
                from app.models import Assignment
                for name in assignment_names:
                    if not name:
                        continue
                    assignment = Assignment.query.filter_by(name=name).first()
                    if not assignment:
                        assignment = Assignment(name=name)
                        db.session.add(assignment)
                        db.session.flush()
                    if assignment not in asset.assignments:
                        asset.assignments.append(assignment)

            # Lieferant-Zuordnung (global_supplier_id)
            if supplier_id:
                from app.models import Supplier
                supplier = Supplier.query.get(supplier_id)
                if supplier:
                    print(f'[DEBUG] Lieferant-Zuordnung für Asset: {asset.name}: {supplier.name}')
                    if hasattr(asset, 'suppliers') and supplier not in asset.suppliers:
                        asset.suppliers.append(supplier)
                    elif hasattr(asset, 'supplier_id'):
                        asset.supplier_id = supplier.id

            if category_idx is not None:
                csv_cat_val = row[category_idx].strip() if category_idx < len(row) else None
                if csv_cat_val and csv_cat_val in assignment_mapping:
                    a_obj = assignment_mapping[csv_cat_val]
                    if a_obj and a_obj not in asset.assignments:
                        asset.assignments.append(a_obj)

            db.session.add(asset)
            imported += 1
    print(f'[DEBUG] Insgesamt importierte Assets: {imported} (letzte Zeile: {row_num})')
    db.session.commit()
    flash(f'{imported} Assets importiert!', 'success')
    session.pop('import_csv_content', None)
    session.pop('import_csv_headers', None)
    return redirect(url_for('import_assets.import_assets_upload'))
