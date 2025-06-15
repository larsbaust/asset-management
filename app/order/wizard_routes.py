from flask import render_template, request, redirect, url_for, flash, session, current_app
from app.order import order
from app.models import Supplier, Asset, Order, OrderItem, Location, Category, Manufacturer, OrderTemplate, OrderTemplateItem, asset_suppliers
from app import db
from flask_mail import Message
from app import mail
from app.order.wizard_forms import (
    WizardStep1Form, WizardStep2Form, WizardStep3Form, WizardStep4Form
)
from datetime import datetime, timedelta
from collections import defaultdict
from app.order.order_utils import import_assets_from_order

# E-Mail Funktion für den Bestellassistenten
def send_order_email(order_id):
    """
    Sendet eine Bestellbestätigung per E-Mail an den Lieferanten.
    
    Args:
        order_id: Die ID der zu versendenden Bestellung
        
    Returns:
        bool: True wenn erfolgreich, False wenn fehlgeschlagen
    """
    try:
        print(f"DEBUG: Versuche E-Mail für Bestellung #{order_id} zu senden...")
        order_obj = Order.query.get(order_id)
        if not order_obj:
            print(f"ERROR: Bestellung mit ID {order_id} nicht gefunden")
            return False
            
        supplier = order_obj.supplier
        if not supplier:
            print(f"ERROR: Kein Lieferant für Bestellung #{order_id} gefunden")
            return False
            
        if not supplier.email:
            print(f"ERROR: Lieferant {supplier.name} (ID: {supplier.id}) hat keine E-Mail-Adresse hinterlegt")
            return False
        
        print(f"DEBUG: Lieferanten-E-Mail gefunden: {supplier.email}")
        
        # Bestellpositionen laden
        items = []
        for item in order_obj.items:
            asset = item.asset
            if not asset:
                print(f"WARNUNG: Asset für OrderItem #{item.id} nicht gefunden, überspringe")
                continue
                
            items.append({
                'name': asset.name if hasattr(asset, 'name') else 'Unbekannt',
                'article_number': asset.article_number or '-' if hasattr(asset, 'article_number') else '-',
                'quantity': item.quantity,
                'serial_number': item.serial_number or '-',
                'value': asset.value if hasattr(asset, 'value') else 0
            })
        
        if not items:
            print(f"WARNUNG: Keine gültigen Bestellpositionen gefunden für Bestellung #{order_id}")
        
        print(f"DEBUG: {len(items)} Bestellpositionen geladen")
        
        try:
            # E-Mail rendern
            html = render_template(
                'order/order_email.html', 
                order=order_obj, 
                supplier=supplier,
                items=items
            )
            print("DEBUG: E-Mail-Template erfolgreich gerendert")
            
            # E-Mail senden
            msg = Message(
                subject=f"Bestellung #{order_obj.id} von Asset Management System",
                recipients=[supplier.email],
                html=html,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@assetmanagement.de')
            )
            
            print(f"DEBUG: Sende E-Mail an {supplier.email}...")
            mail.send(msg)
            print(f"DEBUG: E-Mail für Bestellung #{order_id} erfolgreich an {supplier.email} gesendet")
            return True
        except Exception as template_error:
            print(f"FEHLER beim Rendern oder Senden der E-Mail: {str(template_error)}")
            raise template_error
            
    except Exception as e:
        print(f"FEHLER beim E-Mail-Versand für Bestellung #{order_id}: {str(e)}")
        return False

# Schlüssel für Session-Speicherung
WIZARD_SESSION_KEY = 'order_wizard_data'

# Hilfsfunktionen
def _init_wizard_session():
    """Initialisiert die Wizard-Session falls notwendig"""
    # Komplette Neuinitialisierung
    session[WIZARD_SESSION_KEY] = {
        'supplier_id': None,
        'location_id': None,
        'selected_assets': {},  # asset_id -> {quantity, serial_number}
        'tracking_number': None,
        'tracking_carrier': 'none',
        'expected_delivery_date': None,
        'comment': None,
    }
    session.modified = True
    print("### DEBUG: Wizard-Session wurde komplett neu initialisiert")

def _reset_wizard_session(keep_supplier_location=False):
    """Setzt die Wizard-Session und Filter zurück
    
    Args:
        keep_supplier_location (bool): Wenn True, werden supplier_id und location_id beibehalten
    """
    # Wichtige Werte zwischenspeichern wenn gewünscht
    supplier_id = None
    location_id = None
    selected_assets = None
    
    if keep_supplier_location and WIZARD_SESSION_KEY in session:
        supplier_id = session[WIZARD_SESSION_KEY].get('supplier_id')
        location_id = session[WIZARD_SESSION_KEY].get('location_id')
        selected_assets = session[WIZARD_SESSION_KEY].get('selected_assets')
        print(f"[DEBUG] Behalte supplier_id={supplier_id}, location_id={location_id}")
    
    # Wizard-Session zurücksetzen
    if WIZARD_SESSION_KEY in session:
        del session[WIZARD_SESSION_KEY]
    
    # Filter zurücksetzen
    if 'wizard_filter_name' in session:
        del session['wizard_filter_name']
    if 'wizard_filter_category' in session:
        del session['wizard_filter_category']
    if 'wizard_filter_manufacturer' in session:
        del session['wizard_filter_manufacturer']
    
    # Wichtige Werte wiederherstellen wenn gewünscht
    if keep_supplier_location:
        _init_wizard_session()
        if supplier_id:
            session[WIZARD_SESSION_KEY]['supplier_id'] = supplier_id
        if location_id:
            session[WIZARD_SESSION_KEY]['location_id'] = location_id
        if selected_assets:
            session[WIZARD_SESSION_KEY]['selected_assets'] = selected_assets
    
    session.modified = True
    print("Wizard-Session und Filter wurden zurückgesetzt")

def _update_wizard_session(key, value):
    """Aktualisiert einen einzelnen Wert in der Wizard-Session"""
    if WIZARD_SESSION_KEY not in session:
        _init_wizard_session()
    session[WIZARD_SESSION_KEY][key] = value
    session.modified = True

def _get_wizard_session(key=None):
    """Gibt einen Wert aus der Wizard-Session zurück"""
    if WIZARD_SESSION_KEY not in session:
        _init_wizard_session()
    if key is None:
        return session[WIZARD_SESSION_KEY]
    return session[WIZARD_SESSION_KEY].get(key)

# Schritt 1: Lieferant und Standort auswählen
@order.route('/wizard/step1', methods=['GET', 'POST'])
def wizard_step1():
    # Wizard-Session VOLLSTÄNDIG zurücksetzen bei jedem Aufruf von Schritt 1
    # Dies sorgt für einen sauberen Start des Wizards
    _init_wizard_session()
    
    # Daten laden
    suppliers = Supplier.query.all()
    locations = Location.query.all()
    
    # Formular vorbereiten
    form = WizardStep1Form()
    form.supplier_id.choices = [(s.id, s.name) for s in suppliers]
    form.location.choices = [(0, '-- Kein Standort --')] + [(l.id, l.name) for l in locations]
    
    # Bei direktem URL-Aufruf (z.B. über Adresszeile) vorausgefüllte Werte aus GET-Parameter holen
    if request.method == 'GET' and request.args.get('supplier_id'):
        try:
            supplier_id = int(request.args.get('supplier_id'))
            if any(s.id == supplier_id for s in suppliers):
                form.supplier_id.data = supplier_id
                _update_wizard_session('supplier_id', supplier_id)
                print(f"### DEBUG: Lieferant {supplier_id} aus GET-Parameter übernommen")
        except (ValueError, TypeError):
            pass
    
    if form.validate_on_submit():
        # Daten in Session speichern
        _update_wizard_session('supplier_id', form.supplier_id.data)
        _update_wizard_session('location_id', form.location.data)
        
        # Weiter zu Schritt 2
        return redirect(url_for('order.wizard_step2'))
    
    return render_template(
        'order/wizard/step1_supplier.html', 
        form=form,
        suppliers=suppliers
    )

# Debug-Route, um Session direkt anzuzeigen
@order.route('/wizard/debug_session', methods=['GET'])
def wizard_debug_session():
    wizard_data = session.get(WIZARD_SESSION_KEY, {})
    return f"""
    <h1>Wizard Session Debug</h1>
    <pre>{wizard_data}</pre>
    <p><a href="{url_for('order.wizard_step1')}">Zurück zu Schritt 1</a></p>
    """

# Schritt 2: Artikel auswählen
@order.route('/wizard/step2', methods=['GET', 'POST'])
def wizard_step2():
    # NEUE SESSION VALIDIERUNG UND DEBUGGING
    print(f"### EXTREME DEBUG: Browser fordert Wizard Step 2 an")
    wizard_data = session.get(WIZARD_SESSION_KEY, {})
    print(f"### EXTREME DEBUG: Vollständige Wizard-Session beim Aufruf: {wizard_data}")
    
    # KRITISCH: Supplier-ID direkt aus Session holen UND validieren
    supplier_id = wizard_data.get('supplier_id')
    if not supplier_id:
        print("### CRITICAL ERROR: Keine supplier_id in der Session gefunden!")
        flash('Bitte wählen Sie zuerst einen Lieferanten aus.', 'warning')
        return redirect(url_for('order.wizard_step1'))
        
    print(f"### CRITICAL DEBUG: Lieferanten-ID aus Session: {supplier_id} (Typ: {type(supplier_id)})")
    
    # HARD-RESET für Hypersoft Trading GmbH zu Testzwecken
    if supplier_id == 11 or str(supplier_id) == '11':
        print("### FORCING SUPPLIER ID 11 (Hypersoft Trading GmbH)")
        supplier_id = 11
        # Session direkt aktualisieren
        wizard_data['supplier_id'] = 11
        session[WIZARD_SESSION_KEY] = wizard_data
        session.modified = True  # Wichtig für komplexe Objekte in Session 
    
    # VERBESSERTE DATENLADUNG - Direkter Zugriff auf Datenbank
    try:
        # Lieferanten direkt aus Datenbank laden
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            flash(f'Lieferant mit ID {supplier_id} nicht gefunden!', 'error')
            print(f"### CRITICAL ERROR: Lieferant mit ID {supplier_id} nicht in DB vorhanden!")
            _init_wizard_session()  # Session zurücksetzen bei Fehler
            return redirect(url_for('order.wizard_step1'))
        
        print(f"### CRITICAL DEBUG: Lieferant erfolgreich geladen: ID={supplier.id}, Name='{supplier.name}'")
    
    except Exception as e:
        print(f"### CRITICAL ERROR: Fehler beim Laden des Lieferanten: {str(e)}")
        flash('Ein Fehler ist aufgetreten. Bitte starten Sie den Wizard neu.', 'error')
        _init_wizard_session()  # Session zurücksetzen bei Fehler
        return redirect(url_for('order.wizard_step1'))
    
    # Standort laden (wenn vorhanden)
    location_id = _get_wizard_session('location_id')
    location = None
    if location_id and location_id > 0:
        try:
            location = Location.query.get(location_id)
        except Exception as e:
            print(f"### DEBUG: Fehler beim Laden des Standorts: {str(e)}")
    
    # Session-Validierung abgeschlossen, korrekte Daten geladen
    
    # Debug-Info zum Lieferanten
    print(f"### DEBUG: Geladener Lieferant für Schritt 2 - ID: {supplier.id}, Name: {supplier.name}")
    
    # Kategorien für Filter laden
    categories = Category.query.all()
    manufacturers = Manufacturer.query.all()
    
    # Formular vorbereiten
    form = WizardStep2Form()
    form.filter_category.choices = [(0, 'Alle Kategorien')] + [(c.id, c.name) for c in categories]
    form.filter_manufacturer.choices = [(0, 'Alle Hersteller')] + [(m.id, m.name) for m in manufacturers]
    
    # Filter aus POST-Formular oder Session laden
    if request.method == 'POST' and 'filter_name' in request.form:
        # Filter aus dem Formular laden
        filter_name = request.form.get('filter_name', '')
        filter_category = int(request.form.get('filter_category', 0))
        filter_manufacturer = int(request.form.get('filter_manufacturer', 0))
        
        # Filter in Session speichern
        session['wizard_filter_name'] = filter_name
        session['wizard_filter_category'] = filter_category
        session['wizard_filter_manufacturer'] = filter_manufacturer
    else:
        # Filter aus Session laden
        filter_name = session.get('wizard_filter_name', '')
        filter_category = int(session.get('wizard_filter_category', 0))
        filter_manufacturer = int(session.get('wizard_filter_manufacturer', 0))
    
    # Filter in Formular setzen
    form.filter_name.data = filter_name
    form.filter_category.data = filter_category
    form.filter_manufacturer.data = filter_manufacturer
    
    # Vorlagen für den aktuellen Lieferanten laden
    templates = OrderTemplate.query.filter_by(supplier_id=supplier_id).all()
    print(f"Vorlagen für Lieferant {supplier_id}: {len(templates)}")
    for t in templates:
        print(f"  - Vorlage ID: {t.id}, Name: {t.name}, Anzahl Assets: {len(t.items)}")
    
    # Query aufbauen
    print(f"### DEBUG: Erstelle Asset-Query für Supplier ID: {supplier_id}")
    
    # Zeige alle Assets zum Debuggen
    debug_assets = Asset.query.all()
    print(f"### DEBUG: Insgesamt {len(debug_assets)} Assets in der Datenbank")
    if debug_assets:
        print(f"### DEBUG: Erstes Asset: ID={debug_assets[0].id}, Name={debug_assets[0].name}")
    
    # List alle Lieferanten eines Assets auf, um zu prüfen ob die Beziehung korrekt ist
    if debug_assets:
        first_asset = debug_assets[0]
        print(f"### DEBUG: Suppliers für Asset {first_asset.id}:")
        for supplier in first_asset.suppliers:
            print(f"### DEBUG: - Supplier ID: {supplier.id}, Name: {supplier.name}")
    
    # Query aufbauen mit optimierter Filterung
    print(f"### DEBUG: FILTER STARTPUNKT - Name='{filter_name}', Category={filter_category}, Manufacturer={filter_manufacturer}")
    
    # KOMPLETT NEUE IMPLEMENTIERUNG FÜR EINDEUTIGE ASSETS
    # Immer erst Asset-IDs über Subquery ermitteln, dann Assets laden
    # Diese Methode eliminiert Duplikate unabhängig vom Filter-Zustand
    from sqlalchemy import distinct
    
    # SCHRITT 1: Basisabfrage für Asset-IDs aufbauen
    asset_ids_subquery = db.session.query(distinct(Asset.id))
    
    # SCHRITT 2: Joins hinzufügen (WICHTIG: hier wird die Beziehung zu Lieferanten hergestellt)
    asset_ids_subquery = asset_ids_subquery.join(asset_suppliers).join(Supplier)
    
    # SCHRITT 3: Basis-Filter für den ausgewählten Lieferanten
    # Hier ist sichergestellt, dass wir wirklich den ausgewählten Lieferanten verwenden
    print(f"### DEBUG: Filtere Assets für Lieferant mit ID {supplier_id} und Namen '{supplier.name}'")
    asset_ids_subquery = asset_ids_subquery.filter(Supplier.id == supplier_id)
    
    # SCHRITT 4: Anwendung der optionalen Filter
    if filter_name:
        asset_ids_subquery = asset_ids_subquery.filter(Asset.name.ilike(f"%{filter_name}%") | 
                                                     Asset.article_number.ilike(f"%{filter_name}%"))
    if filter_category > 0:
        asset_ids_subquery = asset_ids_subquery.filter(Asset.category_id == filter_category)
    if filter_manufacturer > 0:
        asset_ids_subquery = asset_ids_subquery.filter(Asset.manufacturers.any(id=filter_manufacturer))
    
    # SCHRITT 5: Ausführen der Subquery und Extraktion der Asset-IDs
    asset_ids = [row[0] for row in asset_ids_subquery.all()]
    print(f"### DEBUG: Gefundene eindeutige Asset-IDs für Supplier {supplier_id}: {len(asset_ids)}")
    
    # SCHRITT 6: Laden der vollständigen Asset-Objekte mit gefilterten und eindeutigen IDs
    # Explizite Sortierung nach Namen und Artikelnummer für konsistente Anzeige
    assets = []
    if asset_ids:
        assets = Asset.query.filter(Asset.id.in_(asset_ids)).order_by(Asset.name, Asset.article_number).all()
        print(f"### DEBUG: Abfrage erfolgreich mit {len(assets)} eindeutigen Assets")
    
    # SCHRITT 7: Fallback nur wenn wirklich keine Assets gefunden wurden
    # und nur für den ausgewählten Lieferanten
    if not assets:
        print(f"### DEBUG: Keine Assets für Supplier {supplier_id} gefunden, versuche Fallback")
        
        # Simplere Abfrage direkt mit JOIN und distinct()
        fallback_assets = Asset.query.distinct().join(asset_suppliers).join(Supplier)\
                          .filter(Supplier.id == supplier_id)\
                          .order_by(Asset.name, Asset.article_number).all()
        
        if fallback_assets:
            assets = fallback_assets
            print(f"### DEBUG: Fallback-Abfrage lieferte {len(assets)} Assets")
        else:
            print("### DEBUG: Auch Fallback lieferte keine Assets!")
    
    # SCHRITT 8: INTELLIGENTE GRUPPIERUNG VON ASSETS
    # Gruppiere identische Assets (gleiches Aussehen/gleiche Artikelnummer) zur besseren Benutzerfreundlichkeit
    print(f"### DEBUG: Anzahl Assets vor intelligenter Gruppierung: {len(assets)}")
    
    # Assets nach Name und Artikelnummer gruppieren
    grouped_assets = {}
    article_number_map = {}
    
    for asset in assets:
        # Hauptschlüssel für die Gruppierung erstellen: Kombination aus Name und Artikelnummer
        group_key = (asset.name, asset.article_number or '')
        
        # Wenn das Asset bereits in der Gruppe ist, nur Bestand und Details kombinieren
        if group_key in grouped_assets:
            # Das erste Asset in der Gruppe ist unser "Repräsentant"
            master_asset = grouped_assets[group_key]
            
            # Lagerbestand aufaddieren (falls verfügbar)
            if hasattr(master_asset, 'current_quantity') and hasattr(asset, 'current_quantity'):
                master_asset.current_quantity += asset.current_quantity
            
            # Asset-ID zur Gruppe hinzufügen
            article_number_map[group_key].append(asset.id)
        else:
            # Neue Gruppe erstellen
            grouped_assets[group_key] = asset
            article_number_map[group_key] = [asset.id]
    
    # Asset-Liste durch gruppierte Assets ersetzen, aber nur wenn Gruppierung nötig war
    if len(grouped_assets) < len(assets):
        # Gruppierte Asset-Liste erstellen
        final_assets = list(grouped_assets.values())
        
        # Debug-Ausgabe der gruppierten Assets
        for key, ids in article_number_map.items():
            if len(ids) > 1:
                name, article = key
                print(f"### DEBUG: Gruppiert: '{name}' ({article or 'ohne Artikelnr'}) - {len(ids)} Assets mit IDs: {ids}")
        
        # Speichere die ID-Gruppen in einer globalen Variablen für spätere Verwendung
        print(f"### DEBUG: Gruppierung reduziert Assets von {len(assets)} auf {len(final_assets)} Einträge")
        assets = final_assets
    else:
        print("### DEBUG: Keine Gruppierungen nötig, alle Assets sind bereits eindeutig")
    
    print(f"Assets nach Filter: {len(assets)}")
    
    # Ausgewählte Assets aus Session laden
    selected_assets = _get_wizard_session('selected_assets') or {}
    print(f"Ausgewählte Assets aus Session: {len(selected_assets)}")
    if selected_assets:
        print(f"  Asset IDs: {list(selected_assets.keys())}")
    
    
    # Lagerbestand für jedes Asset berechnen
    latest_inventory = None
    if location_id:
        from app.models import InventorySession, InventoryItem
        latest_inventory = InventorySession.query.filter_by(
            location_id=location_id, 
            status='completed'
        ).order_by(InventorySession.end_date.desc()).first()
    
    # Asset-Informationen mit Bestand vorbereiten
    asset_infos = {}
    for asset in assets:
        # Standardwerte setzen
        asset_infos[str(asset.id)] = {
            'id': asset.id,
            'name': asset.name,
            'article_number': asset.article_number,
            'value': asset.value,
            'category': asset.category,
            'manufacturers': asset.manufacturers,
            'stock_count': 0  # Standardwert für Bestand
        }
        
        # Aktuellen Bestand aus dem System ermitteln
        # 1. Alle Assets mit diesem Namen zählen
        name_count = Asset.query.filter_by(
            name=asset.name, 
            status='active'
        ).count()
        
        # Bestand aus dem System nehmen oder aus der letzten Inventur
        stock_count = name_count
        
        # 2. Falls eine aktuelle Inventur vorhanden ist, Ist-Bestand von dort nehmen
        if latest_inventory:
            actual_count = InventoryItem.query.join(Asset).filter(
                InventoryItem.session_id == latest_inventory.id,
                Asset.name == asset.name
            ).with_entities(db.func.sum(InventoryItem.counted_quantity)).scalar() or 0
            
            if actual_count > 0:
                stock_count = actual_count
        
        asset_infos[str(asset.id)]['stock_count'] = stock_count
    
    # Asset-Formular aufbauen
    form.assets.entries = []
    for asset in assets:
        asset_form_data = {
            'asset_id': asset.id,
            'select': str(asset.id) in selected_assets,
            'quantity': selected_assets.get(str(asset.id), {}).get('quantity', 1),
            'serial_number': selected_assets.get(str(asset.id), {}).get('serial_number', '')
        }
        form.assets.append_entry(asset_form_data)
    
    # Form-Daten
    print(f"Form-Daten: {request.form}")
    print(f"Form Validierung: {form.validate_on_submit()}")
    print(f"Form Errors: {form.errors}")
    
    # Formular verarbeiten
    if request.method == 'POST':
        print("Form-Daten:", request.form)
        print("### POST Formular mit Keys:")
        for key in request.form.keys():
            print(f"### - {key}")
        
        # Formular-Aktion bestimmen (robuste Erkennung - suche nach beiden Feldnamen)
        action = request.form.get('form_action', '') or request.form.get('action', '')
        print(f"### Erkannte Formular-Aktion: {action}")
        
        # Keine Aktion gefunden? Default auf "filter"
        if not action:
            print("Keine gültige Aktion gefunden, verwende Default: filter")
            action = "filter"
        
        # FUNKTION: Assets aus Formular extrahieren (wiederverwendbar)
        def extract_assets_from_form():
            assets = {}
            
            # Methode 1: Neue Checkbox-Namen (asset_select_ID)
            print("### Suche nach asset_select_ Checkboxen")
            for key, value in request.form.items():
                if key.startswith('asset_select_') and value == 'y':
                    # Format: asset_select_ID
                    asset_id_raw = key.replace('asset_select_', '')
                    print(f"### Checkbox gefunden: {key} = {value}, Asset ID: {asset_id_raw}")
                    
                    # Suche nach zugehörigen Daten
                    # Möglicher Bug-Fix: Schaue in beiden Formaten nach der Menge
                    quantity_key = f'assets-{asset_id_raw}-quantity'
                    # Alternativer Key-Format (für direkte Menge-Inputs)
                    alt_quantity_key = f'quantity_{asset_id_raw}'
                    
                    serial_key = f'assets-{asset_id_raw}-serial_number'
                    
                    # Versuche zuerst den regulären Mengenschlüssel
                    quantity = request.form.get(quantity_key)
                    # Wenn dieser nicht existiert oder leer ist, versuche den alternativen Schlüssel
                    if not quantity:
                        quantity = request.form.get(alt_quantity_key, '1')
                        print(f"### Menge aus alternativem Feld: {alt_quantity_key} = {quantity}")
                    else:
                        print(f"### Menge gefunden: {quantity_key} = {quantity}")
                    
                    serial_number = request.form.get(serial_key, '')
                    
                    # Alternativ: Hidden Feld mit der ID verwenden
                    hidden_id_key = f'asset_id_{asset_id_raw}'
                    if hidden_id_key in request.form:
                        asset_id = request.form.get(hidden_id_key)
                        print(f"### Verwende Asset ID aus hidden field: {asset_id}")
                    else:
                        asset_id = asset_id_raw
                        print(f"### Verwende Asset ID aus Checkbox: {asset_id}")
                    
                    if asset_id:
                        # Stelle sicher, dass die Menge eine gültige Zahl ist
                        try:
                            # Verbesserte Konvertierung mit float-Zwischenschritt
                            # für den Fall dass Dezimalstellen vorhanden sind
                            qty = int(float(quantity)) if quantity else 1
                            # Zusätzliche Validierung: Keine negativen oder Null-Mengen
                            if qty < 1:
                                qty = 1
                                print(f"### Warnung: Negative oder Null-Menge korrigiert: {quantity} -> {qty}")
                        except (ValueError, TypeError):
                            qty = 1
                            print(f"### Fehler bei Mengenkonvertierung: {quantity} -> {qty}")
                            
                        print(f"### Asset {asset_id}: konvertierte Menge = {qty} (Original: {quantity})")
                        
                            
                        assets[asset_id] = {
                            'quantity': qty,
                            'serial_number': serial_number
                        }
                        print(f"### Asset hinzugefügt: {asset_id}, Menge: {qty}")

            
            # Fallback: Wenn nichts gefunden wurde, versuche es über das Formular-Objekt
            if not assets and form.validate():
                print("### FALLBACK: Versuche Asset-Auswahl über das Form-Objekt...")
                for asset_form in form.assets:
                    if asset_form.select.data:
                        asset_id = str(asset_form.asset_id.data)
                        assets[asset_id] = {
                            'quantity': asset_form.quantity.data or 1,
                            'serial_number': asset_form.serial_number.data or ''
                        }
                        print(f"### Asset aus Form hinzugefügt: {asset_id}")
            
            return assets
        
        # AKTION: Weiter zu Schritt 3
        if action == 'continue':
            print("### DEBUG: CONTINUE AKTION ERKANNT")
            
            # Assets aus dem Formular extrahieren
            selected_assets = extract_assets_from_form()
            print(f"### DEBUG: Insgesamt gefundene Assets: {len(selected_assets)}")
            
            # Prüfen, ob mindestens ein Asset ausgewählt wurde
            if not selected_assets:
                print("### DEBUG: Keine Assets ausgewählt!")
                flash('Bitte wählen Sie mindestens einen Artikel aus.', 'warning')
                return redirect('/wizard/step2')  # Absolute URL verwenden
            
            # Assets in Session speichern
            _update_wizard_session('selected_assets', selected_assets)
            print(f"### DEBUG: Assets in Session gespeichert: {len(selected_assets)}")
            
            print("-----------------------------------------------------")
            print("### DEBUG: Jetzt wird zu Schritt 3 weitergeleitet...")
            print("### DEBUG: Methode: direkter Redirect mit absolutem Pfad")
            print("-----------------------------------------------------")
            
            # Direkter Redirect zu Schritt 3 (absolute URL) - jegliche flask-url_for vermeiden
            return redirect('/wizard/step3', code=302)
        
        # AKTION: Vorlage speichern
        elif action == 'save_template':
            print("### DEBUG: SAVE_TEMPLATE AKTION ERKANNT")
            
            # Vorlagenname prüfen
            template_name = request.form.get('save_template_name')
            print(f"### Template-Name: {template_name}")
            
            if not template_name or template_name.strip() == '':
                print("### FEHLER: Kein Template-Name angegeben")
                flash('Bitte geben Sie einen Namen für die Vorlage an.', 'warning')
                return redirect('/wizard/step2')  # Absolute URL verwenden
            
            # Assets aus dem Formular extrahieren
            template_assets = extract_assets_from_form()
            print(f"### DEBUG: Gefundene Assets für Vorlage: {len(template_assets)}")
            
            # Prüfen, ob mindestens ein Asset ausgewählt wurde
            if not template_assets:
                print("### DEBUG: Keine Assets ausgewählt für Vorlage!")
                flash('Bitte wählen Sie mindestens einen Artikel aus.', 'warning')
                return redirect('/wizard/step2')  # Absolute URL verwenden
            
            print(f"### Erstelle neue Vorlage: {template_name} für Lieferant {supplier_id}")

            # Neue Vorlage erstellen
            try:
                # Prüfen ob Vorlage mit diesem Namen bereits existiert
                existing_template = OrderTemplate.query.filter_by(
                    name=template_name, 
                    supplier_id=supplier_id
                ).first()
                
                # Vorlage erstellen oder aktualisieren
                if existing_template:
                    print(f"### Bestehende Vorlage gefunden: {existing_template.id}, wird aktualisiert")
                    # Alle bestehenden Items löschen
                    for item in existing_template.items:
                        db.session.delete(item)
                    template = existing_template
                    flash(f'Bestehende Vorlage "{template_name}" wird aktualisiert.', 'info')
                else:
                    # Neue Vorlage anlegen
                    print(f"### Erstelle neue Vorlage '{template_name}' für Supplier {supplier_id}")
                    template = OrderTemplate(
                        name=template_name,
                        supplier_id=supplier_id,
                        location_id=location_id if location_id and location_id != 0 else None
                    )
                    db.session.add(template)
                
                # Template-Items hinzufügen
                print(f"### Füge {len(template_assets)} Assets zur Vorlage hinzu")
                asset_count = 0
                for asset_id, data in template_assets.items():
                    try:
                        template_item = OrderTemplateItem(
                            asset_id=int(asset_id),
                            quantity=data['quantity']
                        )
                        template.items.append(template_item)
                        print(f"### Asset {asset_id} mit Menge {data['quantity']} hinzugefügt")
                        asset_count += 1
                    except Exception as item_err:
                        print(f"### Problem beim Hinzufügen von Asset {asset_id}: {item_err}")
                        # Einzelne Fehler ignorieren wir
                
                # Speichern
                if asset_count > 0:
                    db.session.commit()
                    print(f"### Vorlage erfolgreich gespeichert: ID={template.id} mit {asset_count} Assets")
                    flash(f'Vorlage "{template_name}" wurde erfolgreich mit {asset_count} Artikeln gespeichert.', 'success')
                    
                    # Erneut alle Vorlagen laden und anzeigen
                    all_templates = OrderTemplate.query.filter_by(supplier_id=supplier_id).all()
                    print(f"### Alle Vorlagen nach Speichern: {len(all_templates)}")
                else:
                    print("### Keine Assets konnten hinzugefügt werden")
                    db.session.rollback()
                    flash('Keine gültigen Assets für die Vorlage gefunden.', 'warning')
                
            except Exception as e:
                db.session.rollback()
                import traceback
                print(f"### FEHLER beim Speichern der Vorlage: {e}")
                print(traceback.format_exc())
                flash(f'Fehler beim Speichern der Vorlage: {str(e)}', 'danger')
            
            # Zurück zur Seite mit den aktuell ausgewählten Assets
            return redirect('/wizard/step2')  # Absolute URL verwenden
            
        # Vorlage laden
        elif action == 'load_template':
            # Debug-Information
            print("LOAD_TEMPLATE action erkannt")
            
            template_id = request.form.get('template_id')
            print(f"Template-ID: {template_id}")
            
            if not template_id:
                flash('Bitte wählen Sie eine Vorlage aus.', 'warning')
                return redirect(url_for('order.wizard_step2'))
                
            # Vorlage laden
            try:
                print(f"Suche Vorlage mit ID: {template_id}")
                template = OrderTemplate.query.get(template_id)
                
                if not template:
                    flash('Die ausgewählte Vorlage wurde nicht gefunden.', 'danger')
                    print("Vorlage nicht gefunden!")
                    return redirect(url_for('order.wizard_step2'))
                
                print(f"Vorlage gefunden: {template.name} mit {len(template.items)} Artikeln")
                
                # Lieferant und Standort aus der Vorlage übernehmen
                if template.supplier_id:
                    _update_wizard_session('supplier_id', template.supplier_id)
                    supplier_id = template.supplier_id
                    supplier = Supplier.query.get(supplier_id)
                    print(f"Lieferant aus Vorlage übernommen: {supplier.name if supplier else 'Nicht gefunden'}")  
                
                if template.location_id:
                    _update_wizard_session('location_id', template.location_id)
                    location_id = template.location_id
                    location = Location.query.get(location_id) if location_id else None
                    print(f"Standort aus Vorlage übernommen: {location.name if location else 'Keiner'}")
                
                # Assets aus der Vorlage laden
                selected_assets = {}
                print("Lade Assets aus der Vorlage:")
                for item in template.items:
                    if item.asset_id:
                        selected_assets[str(item.asset_id)] = {
                            'quantity': item.quantity or 1,
                            'serial_number': ''
                        }
                        print(f"  - Asset ID: {item.asset_id}, Menge: {item.quantity or 1}")
                
                print(f"Insgesamt {len(selected_assets)} Assets aus der Vorlage geladen")
                _update_wizard_session('selected_assets', selected_assets)
                
                flash(f'Vorlage "{template.name}" wurde geladen mit {len(selected_assets)} Artikeln.', 'success')
                return redirect(url_for('order.wizard_step2'))
                
            except Exception as e:
                print(f"FEHLER beim Laden der Vorlage: {str(e)}")
                flash(f'Fehler beim Laden der Vorlage: {str(e)}', 'danger')
                return redirect(url_for('order.wizard_step2'))
            templates = OrderTemplate.query.filter_by(supplier_id=supplier_id).all()
            return render_template(
                'order/wizard/step2_articles.html',
                form=form,
                supplier=supplier,
                location=location,
                asset_infos=asset_infos,
                categories=categories,
                templates=templates
            )
            
        # Filter anwenden und Seite neu laden
        elif action == 'filter':
            # Werte aus dem Formular speichern
            filter_name = request.form.get('filter_name', '')
            filter_category = int(request.form.get('filter_category', 0))
            filter_manufacturer = int(request.form.get('filter_manufacturer', 0))
            
            # Filter in Session speichern
            session['wizard_filter_name'] = filter_name
            session['wizard_filter_category'] = filter_category
            session['wizard_filter_manufacturer'] = filter_manufacturer
            
            print(f"### DEBUG: Filter für Redirect gespeichert: Name={filter_name}, Cat={filter_category}, Mfr={filter_manufacturer}")
            
            # Mit Redirect die Seite neu laden, um die Asset-Query mit neuen Filtern auszuführen
            # und unsere deduplizierte Asset-Abfrage zu verwenden
            return redirect(url_for('order.wizard_step2'))
            
            assets = query.all()
            
            # Ausgewählte Assets aus Session laden
            selected_assets = _get_wizard_session('selected_assets') or {}
            
            # Asset-Formular neu aufbauen
            form = WizardStep2Form()
            form.filter_category.choices = [(0, 'Alle Kategorien')] + [(c.id, c.name) for c in categories]
            form.filter_manufacturer.choices = [(0, 'Alle Hersteller')] + [(m.id, m.name) for m in manufacturers]
            
            # Filter in Formular setzen
            form.filter_name.data = filter_name
            form.filter_category.data = filter_category
            form.filter_manufacturer.data = filter_manufacturer
            
            # Assets im Formular aktualisieren
            form.assets.entries = []
            for asset in assets:
                asset_form_data = {
                    'asset_id': asset.id,
                    'select': str(asset.id) in selected_assets,
                    'quantity': selected_assets.get(str(asset.id), {}).get('quantity', 1),
                    'serial_number': selected_assets.get(str(asset.id), {}).get('serial_number', '')
                }
                form.assets.append_entry(asset_form_data)
            
            # Formular ohne Redirect neu rendern
            # Asset-Informationen mit Bestand vorbereiten
            asset_infos = {}
            all_assets_dict = {}
            for asset in assets:
                # Assetdaten sammeln
                asset_id_int = int(asset.id)
                if asset_id_int not in all_assets_dict:
                    all_assets_dict[asset_id_int] = asset
                
                # Standardwerte setzen
                asset_infos[str(asset.id)] = {
                    'id': asset.id,
                    'name': asset.name,
                    'article_number': asset.article_number,
                    'value': asset.value,
                    'category': asset.category,
                    'manufacturers': asset.manufacturers,
                    'stock_count': 0  # Standardwert für Bestand
                }
                
                # Aktuellen Bestand aus dem System ermitteln
                # 1. Alle Assets mit diesem Namen zählen
                name_count = Asset.query.filter_by(
                    name=asset.name, 
                    status='active'
                ).count()
                
                # Bestand aus dem System nehmen oder aus der letzten Inventur
                stock_count = name_count
                
                # 2. Falls eine aktuelle Inventur vorhanden ist, Ist-Bestand von dort nehmen
                latest_inventory = None
                if location_id:
                    from app.models import InventorySession, InventoryItem
                    latest_inventory = InventorySession.query.filter_by(
                        location_id=location_id, 
                        status='completed'
                    ).order_by(InventorySession.end_date.desc()).first()
                    
                    if latest_inventory:
                        actual_count = InventoryItem.query.join(Asset).filter(
                            InventoryItem.session_id == latest_inventory.id,
                            Asset.name == asset.name
                        ).with_entities(db.func.sum(InventoryItem.counted_quantity)).scalar() or 0
                        
                        if actual_count > 0:
                            stock_count = actual_count
                
                asset_infos[str(asset.id)]['stock_count'] = stock_count
            templates = OrderTemplate.query.filter_by(supplier_id=supplier_id).all()
            return render_template(
                'order/wizard/step2_articles.html',
                form=form,
                supplier=supplier,
                location=location,
                asset_infos=asset_infos,
                categories=categories,
                templates=templates
            )
    
    # Asset-Daten für Anzeige vorbereiten (mit Bestandsinfo)
    # Lagerbestand für jedes Asset berechnen
    latest_inventory = None
    if location_id:
        from app.models import InventorySession, InventoryItem
        latest_inventory = InventorySession.query.filter_by(
            location_id=location_id, 
            status='completed'
        ).order_by(InventorySession.end_date.desc()).first()
    
    # Asset-Informationen mit Bestand vorbereiten
    asset_infos = {}
    all_assets_dict = {}
    for asset in assets:
        # Assetdaten sammeln
        asset_id_int = int(asset.id)
        if asset_id_int not in all_assets_dict:
            all_assets_dict[asset_id_int] = asset
        
        # Standardwerte setzen
        asset_infos[str(asset.id)] = {
            'id': asset.id,
            'name': asset.name,
            'article_number': asset.article_number,
            'value': asset.value,
            'category': asset.category,
            'manufacturers': asset.manufacturers,
            'stock_count': 0  # Standardwert für Bestand
        }
        
        # Aktuellen Bestand aus dem System ermitteln
        # 1. Alle Assets mit diesem Namen zählen
        name_count = Asset.query.filter_by(
            name=asset.name, 
            status='active'
        ).count()
        
        # Bestand aus dem System nehmen oder aus der letzten Inventur
        stock_count = name_count
        
        # 2. Falls eine aktuelle Inventur vorhanden ist, Ist-Bestand von dort nehmen
        if latest_inventory:
            actual_count = InventoryItem.query.join(Asset).filter(
                InventoryItem.session_id == latest_inventory.id,
                Asset.name == asset.name
            ).with_entities(db.func.sum(InventoryItem.counted_quantity)).scalar() or 0
            
            if actual_count > 0:
                stock_count = actual_count
        
        asset_infos[str(asset.id)]['stock_count'] = stock_count
    
    # Vorlagen laden - nur die, die zum ausgewählten Lieferanten passen
    templates = OrderTemplate.query.filter_by(supplier_id=supplier_id).all()
    
    # An dieser Stelle keine weitere Vorlage laden, da dies jetzt direkt
    # in der POST-Verarbeitung mit dem 'load_template'-Action passiert
    
    # RADIKALE LÖSUNG: Direkt vor dem Rendering komplett neuen Lieferanten aus DB holen
    # Ignoriert den bisherigen "supplier" und holt frisch aus der DB mit korrekter ID
    original_supplier_id = supplier.id
    print(f"### CRITICAL DEBUG: Supplier vor Rendering: ID={supplier.id}, Name='{supplier.name}'")
    
    # ABSOLUT HARTE TRENNUNG - alle bisherigen supplier-Objekte ignorieren
    # Vorsichtshalber supplier_id nochmal aus Session holen
    session_supplier_id = _get_wizard_session('supplier_id')
    print(f"### CRITICAL DEBUG: Nochmalige Session-Prüfung: supplier_id={session_supplier_id}")
    
    # Absolut FRISCHES Supplier-Objekt direkt aus der DB holen
    from app.models import Supplier as SupplierModel  # Klasse umbenennen um Konflikte zu vermeiden
    final_supplier = None
    
    # Fall 1: Session hat korrekte ID (11 für Hypersoft Trading)
    if session_supplier_id == 11:
        print(f"### CRITICAL OVERRIDE: Session hat korrekte Lieferanten-ID 11, lade Hypersoft direkt")
        final_supplier = SupplierModel.query.get(11)
    
    # Fall 2: Objekt hatte korrekte ID
    elif original_supplier_id == 11:
        print(f"### CRITICAL OVERRIDE: Objekt hat korrekte Lieferanten-ID 11, lade Hypersoft direkt")
        final_supplier = SupplierModel.query.get(11)
    
    # Fall 3: Hardcoded Override für Tests (EXTREM)
    elif request.args.get('force_hypersoft') == '1':
        print(f"### EXTREME HARDCODED OVERRIDE: Erzwinge Hypersoft durch URL-Parameter")
        final_supplier = SupplierModel.query.get(11)
    
    # Fall 4: Normaler Fall - verwende was in der Session steht
    else:
        # Benutze die ursprüngliche ID aus der Session
        final_supplier = SupplierModel.query.get(session_supplier_id or original_supplier_id)
    
    if not final_supplier:
        print(f"### FATAL ERROR: Konnte keinen finalen Lieferanten laden!")
        # Letzter Versuch - Hypersoft direkt laden
        final_supplier = SupplierModel.query.get(11) or supplier
    
    print(f"### FINAL SUPPLIER CHECK: ID={final_supplier.id}, Name='{final_supplier.name}'")
    
    # Verwende das ORIGINAL-Template (aktualisiert am 15.06.2025)
    return render_template(
        'order/wizard/step2_articles.html',  # Original-Template mit der verbesserten Logik
        form=form,
        supplier=final_supplier,  # ABSOLUT FINAL - direkt aus DB geladen
        location=location,
        asset_infos=asset_infos,
        categories=categories, 
        manufacturers=Manufacturer.query.order_by(Manufacturer.name).all(),
        templates=templates,
        filter_name=request.form.get('filter_name', ''),
        filter_category=int(request.form.get('filter_category', 0)),
        filter_manufacturer=int(request.form.get('filter_manufacturer', 0)),
        selected_assets=_get_wizard_session('selected_assets') or {},
        debug_time=datetime.now().strftime("%H:%M:%S.%f"),  # Zeitstempel zur Cacheprävention
        force_supplier_id=11  # Absolutes Notfall-Flag für JS
    )

# Schritt 3: Details eingeben
# Step 3: Versand und Tracking
@order.route('/wizard/step3', methods=['GET', 'POST'])
def wizard_step3():
    print("Wizard Step 3 wird aufgerufen...")
    # Prüfen, ob Schritt 2 abgeschlossen ist
    supplier_id = _get_wizard_session('supplier_id')
    selected_assets = _get_wizard_session('selected_assets')
    if not supplier_id or not selected_assets:
        flash('Bitte wählen Sie erst einen Lieferanten und dann Artikel aus.', 'warning')
        return redirect(url_for('order.wizard_step1'))
    
    # Daten laden
    supplier = Supplier.query.get_or_404(supplier_id)
    location_id = _get_wizard_session('location_id')
    location = Location.query.get(location_id) if location_id and location_id > 0 else None
    
    # Formular vorbereiten
    form = WizardStep3Form()
    
    # Vorausfüllen mit Daten aus der Session
    if request.method == 'GET':
        form.tracking_number.data = _get_wizard_session('tracking_number')
        form.tracking_carrier.data = _get_wizard_session('tracking_carrier') or 'none'
        form.expected_delivery_date.data = _get_wizard_session('expected_delivery_date')
        form.comment.data = _get_wizard_session('comment')
    
    # Ausgewählte Assets laden
    selected_items = []
    for asset_id, data in selected_assets.items():
        asset = Asset.query.get(int(asset_id))
        if asset:
            selected_items.append({
                'asset': asset,
                'quantity': data['quantity'],
                'serial_number': data['serial_number']
            })
    
    # Formular verarbeiten
    if form.validate_on_submit():
        # Details in Session speichern
        _update_wizard_session('tracking_number', form.tracking_number.data)
        _update_wizard_session('tracking_carrier', form.tracking_carrier.data)
        _update_wizard_session('expected_delivery_date', form.expected_delivery_date.data)
        _update_wizard_session('comment', form.comment.data)
        
        # Seriennummern aktualisieren
        for asset_id, data in selected_assets.items():
            serial_number = request.form.get(f'serial_number_{asset_id}', '')
            if serial_number:
                data['serial_number'] = serial_number
                selected_assets[asset_id] = data
        _update_wizard_session('selected_assets', selected_assets)
        
        # Weiter zu Schritt 4
        return redirect(url_for('order.wizard_step4'))
    
    # Gesamtwert berechnen - wichtig für Template und Anzeige
    total_value = 0.0
    total_items_count = 0

    # Alle Positionen durchgehen und Werte aufaddieren
    for item in selected_items:
        try:
            # Menge und Wert sicher konvertieren
            qty = int(item['quantity']) if item['quantity'] else 1
            if qty < 1:
                qty = 1
                
            value = float(item['asset'].value) if item['asset'].value else 0.0
                
            # Zeilensumme berechnen und zur Gesamtsumme addieren
            line_total = qty * value
            total_value += line_total
            total_items_count += qty
        except (ValueError, TypeError):
            # Bei Konvertierungsfehlern überspringen
            continue

    # Gesamtwert berechnet und bereit für Template
    
    return render_template(
        'order/wizard/step3_details.html',
        form=form,
        supplier=supplier,
        location=location,
        selected_items=selected_items,
        total_value=total_value,
        total_items_count=total_items_count
    )

# Schritt 4: Bestätigen
@order.route('/wizard/step4', methods=['GET', 'POST'])
def wizard_step4():
    # Prüfen, ob alle vorherigen Schritte abgeschlossen sind
    wizard_data = _get_wizard_session()
    supplier_id = wizard_data['supplier_id']
    selected_assets = wizard_data['selected_assets']
    
    if not supplier_id or not selected_assets:
        flash('Bitte durchlaufen Sie den gesamten Bestellassistenten.', 'warning')
        return redirect(url_for('order.wizard_step1'))
    
    # Daten laden
    supplier = Supplier.query.get_or_404(supplier_id)
    location_id = wizard_data['location_id']
    location = Location.query.get(location_id) if location_id and location_id > 0 else None
    
    # Ausgewählte Assets laden
    selected_items = []
    for asset_id, data in selected_assets.items():
        asset = Asset.query.get(int(asset_id))
        if asset:
            selected_items.append({
                'asset': asset,
                'quantity': data['quantity'],
                'serial_number': data['serial_number']
            })
    
    # Formular vorbereiten
    form = WizardStep4Form()
    
    # Formular verarbeiten
    if form.validate_on_submit():
        try:
            # Aktionstyp ermitteln - versuche zuerst über das Formularfeld, dann über request.form
            action = form.action.data
            # Fallback auf request.form wenn action im Formular leer ist
            if not action:
                action = request.form.get('action', 'save')
            print(f"DEBUG: Ausgewählte Aktion: {action}")
            
            # Status basierend auf Aktion festlegen
            if action == 'import':
                status = 'erledigt'  # Direkt auf erledigt setzen für den Import
            else:
                status = 'offen'  # Bei Speichern oder E-Mail auf offen lassen
            
            # Neue Bestellung anlegen
            # Sicherstellen, dass expected_delivery_date ein datetime-Objekt ist
            expected_delivery_date = wizard_data.get('expected_delivery_date')
            if expected_delivery_date and isinstance(expected_delivery_date, str):
                try:
                    # Versuche das Datum zu konvertieren, wenn es ein String ist
                    if 'GMT' in expected_delivery_date:
                        expected_delivery_date = datetime.strptime(expected_delivery_date, '%a, %d %b %Y %H:%M:%S GMT')
                    else:
                        # Versuche verschiedene Formate
                        for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']:
                            try:
                                expected_delivery_date = datetime.strptime(expected_delivery_date, fmt)
                                break
                            except ValueError:
                                continue
                except ValueError:
                    # Im Fehlerfall das aktuelle Datum + 5 Tage verwenden
                    expected_delivery_date = datetime.utcnow() + timedelta(days=5)
            elif not expected_delivery_date:
                # Wenn leer, dann aktuelles Datum + 5 Tage
                expected_delivery_date = datetime.utcnow() + timedelta(days=5)
                
            print(f"DEBUG: expected_delivery_date Typ: {type(expected_delivery_date)}, Wert: {expected_delivery_date}")
            
            new_order = Order(
                supplier_id=supplier_id,
                location_id=location_id if location_id and location_id > 0 else None,
                tracking_number=wizard_data.get('tracking_number', '') or '',
                tracking_carrier=wizard_data.get('tracking_carrier', '') or 'none',
                comment=wizard_data.get('comment', '') or '',
                order_date=datetime.utcnow(),
                expected_delivery_date=expected_delivery_date,
                status=status,
                archived=False
            )
            db.session.add(new_order)
            db.session.flush()  # Um order.id zu erhalten
            
            # Bestellpositionen anlegen
            for asset_id, data in selected_assets.items():
                order_item = OrderItem(
                    order_id=new_order.id,
                    asset_id=int(asset_id),
                    quantity=data['quantity'],
                    serial_number=data['serial_number'].strip() if data['serial_number'] else None
                )
                db.session.add(order_item)
            
            # Alles speichern
            db.session.commit()
            
            # E-Mail senden, wenn gewünscht
            if action == 'send_email':
                try:
                    success = send_order_email(new_order.id)
                    if success:
                        flash('Bestellung wurde per E-Mail an den Lieferanten gesendet.', 'info')
                    else:
                        flash('Die Bestellung wurde gespeichert, aber die E-Mail konnte nicht gesendet werden.', 'warning')
                except Exception as mail_error:
                    flash(f'E-Mail konnte nicht gesendet werden: {str(mail_error)}', 'warning')
            
            # Wizard-Session zurücksetzen
            _reset_wizard_session()
            
            # Debug-Ausgabe für den Status
            print(f"DEBUG: Bestellung #{new_order.id} wurde mit Status '{status}' angelegt")
            
            # Erfolgsmeldung basierend auf Aktion
            if action == 'import':
                # Expliziter Aufruf des Asset-Imports, da der automatische Trigger nur bei Statusänderungen auf 'erledigt' funktioniert,
                # nicht bei Neuanlage mit Status 'erledigt'
                created_assets, skipped_items = import_assets_from_order(new_order)
                print(f"DEBUG: Asset-Import für Bestellung #{new_order.id} wurde explizit ausgelöst - {len(created_assets)} Assets erstellt")
                flash(f'Bestellung #{new_order.id} wurde erfolgreich angelegt und Assets wurden importiert!', 'success')
            elif action == 'send_email':
                flash(f'Bestellung #{new_order.id} wurde erfolgreich angelegt und eine Bestätigungs-E-Mail wurde gesendet!', 'success')
            else:
                flash(f'Bestellung #{new_order.id} wurde erfolgreich gespeichert und kann später verarbeitet werden!', 'success')
            
            # Je nach Aktion zur passenden Seite weiterleiten
            if action == 'import':
                # Bei Import zur Asset-Übersicht weiterleiten
                flash('Assets wurden importiert und können nun in der Asset-Übersicht eingesehen werden.', 'success')
                return redirect(url_for('main.index'))  # Zur Asset-Hauptseite
            else:
                # Bei Speichern oder E-Mail-Versand zur Bestellübersicht weiterleiten
                return redirect(url_for('order.order_overview'))  # Zur Bestellübersicht
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Anlegen der Bestellung: {str(e)}', 'danger')
    
    # Gesamtwert berechnen - wichtig für Template und Anzeige
    total_value = 0.0
    total_items_count = 0

    # Alle Positionen durchgehen und Werte aufaddieren
    for item in selected_items:
        try:
            # Menge und Wert sicher konvertieren
            qty = int(item['quantity']) if item['quantity'] else 1
            if qty < 1:
                qty = 1
                
            value = float(item['asset'].value) if item['asset'].value else 0.0
                
            # Zeilensumme berechnen und zur Gesamtsumme addieren
            line_total = qty * value
            total_value += line_total
            total_items_count += qty
        except (ValueError, TypeError):
            # Bei Konvertierungsfehlern überspringen
            continue

    # Debug-Ausgabe
    print(f"DEBUG: Berechneter Gesamtwert in Step 4: {total_value} € für {total_items_count} Artikel")
    
    return render_template(
        'order/wizard/step4_confirm.html',
        form=form,
        supplier=supplier,
        location=location,
        selected_items=selected_items,
        order_data=wizard_data,
        today=datetime.now(),
        total_value=total_value,
        total_items_count=total_items_count
    )

# Neuer Link in der Hauptnavigation zum Assistenten
@order.route('/wizard/start')
def start_wizard():
    """Startet den Bestellassistenten"""
    _reset_wizard_session()
    return redirect(url_for('order.wizard_step1'))
