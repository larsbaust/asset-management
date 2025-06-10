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
    if WIZARD_SESSION_KEY not in session:
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

def _reset_wizard_session():
    """Setzt die Wizard-Session und Filter zurück"""
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
    
    session.modified = True
    print("Wizard-Session und Filter wurden vollständig zurückgesetzt")

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
    # Wizard-Session initialisieren
    _init_wizard_session()
    
    # Daten laden
    suppliers = Supplier.query.all()
    locations = Location.query.all()
    
    # Formular vorbereiten
    form = WizardStep1Form()
    form.supplier_id.choices = [(s.id, s.name) for s in suppliers]
    form.location.choices = [(0, '-- Kein Standort --')] + [(l.id, l.name) for l in locations]
    
    # Vorausfüllen mit bestehenden Daten aus der Session
    if request.method == 'GET':
        supplier_id = _get_wizard_session('supplier_id')
        location_id = _get_wizard_session('location_id')
        if supplier_id:
            form.supplier_id.data = supplier_id
        if location_id:
            form.location.data = location_id
    
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

# Schritt 2: Artikel auswählen
@order.route('/wizard/step2', methods=['GET', 'POST'])
def wizard_step2():
    # Prüfen, ob Schritt 1 abgeschlossen ist
    supplier_id = _get_wizard_session('supplier_id')
    if not supplier_id:
        flash('Bitte wählen Sie zuerst einen Lieferanten aus.', 'warning')
        return redirect(url_for('order.wizard_step1'))
    
    # Daten laden
    supplier = Supplier.query.get_or_404(supplier_id)
    location_id = _get_wizard_session('location_id')
    location = Location.query.get(location_id) if location_id and location_id > 0 else None
    
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
    
    # Asset-Query mit optimierter Filterung
    # Verwende direkte SQL-Joins statt any()
    query = Asset.query.join(asset_suppliers).join(Supplier)
    query = query.filter(Supplier.id == supplier_id)
    
    # Filter anwenden
    if filter_name:
        query = query.filter(Asset.name.ilike(f"%{filter_name}%"))
    if filter_category > 0:
        query = query.filter(Asset.category_id == filter_category)
    if filter_manufacturer > 0:
        query = query.filter(Asset.manufacturers.any(id=filter_manufacturer))

    print(f"### DEBUG: SQL für Assets: {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
    
    # Ergebnisse abrufen
    try:
        assets = query.all()
        print(f"### DEBUG: Abfrage erfolgreich mit {len(assets)} Ergebnissen")
        
        # Wenn keine Assets gefunden wurden, zeige alle Assets als Fallback
        # Dies sorgt dafür, dass beim ersten Laden immer Assets angezeigt werden
        if not assets:
            print(f"### DEBUG: Keine Assets für Supplier {supplier_id} gefunden, zeige alle Assets")
            assets = Asset.query.all()
            print(f"### DEBUG: FALLBACK - zeige alle {len(assets)} Assets an")
    except Exception as e:
        print(f"### DEBUG: SQL-Fehler: {str(e)}")
        # Fallback bei Fehler: Alle Assets anzeigen
        assets = Asset.query.all()
        print(f"### DEBUG: FEHLER-FALLBACK - zeige alle {len(assets)} Assets an")
    print(f"Assets nach Filter: {len(assets)}")
    
    # Ausgewählte Assets aus Session laden
    selected_assets = _get_wizard_session('selected_assets') or {}
    print(f"Ausgewählte Assets aus Session: {len(selected_assets)}")
    if selected_assets:
        print(f"  Asset IDs: {list(selected_assets.keys())}")
    
    
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
                    quantity_key = f'assets-{asset_id_raw}-quantity'
                    serial_key = f'assets-{asset_id_raw}-serial_number'
                    quantity = request.form.get(quantity_key, '1')
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
                        assets[asset_id] = {
                            'quantity': int(quantity) if quantity and quantity.isdigit() else 1,
                            'serial_number': serial_number
                        }
                        print(f"### Asset hinzugefügt: {asset_id}, Menge: {quantity}")
            
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
            
        # Nur Filter anwenden, Seite ohne Redirect neu laden
        elif action == 'filter':
            filter_name = request.form.get('filter_name', '')
            filter_category = int(request.form.get('filter_category', 0))
            filter_manufacturer = int(request.form.get('filter_manufacturer', 0))
            
            # Filter in Session speichern
            session['wizard_filter_name'] = filter_name
            session['wizard_filter_category'] = filter_category
            session['wizard_filter_manufacturer'] = filter_manufacturer
            
            # Query neu aufbauen mit aktuellen Filtern
            query = Asset.query
            if filter_name:
                query = query.filter(Asset.name.ilike(f"%{filter_name}%"))
            if filter_category > 0:
                query = query.filter(Asset.category_id == filter_category)
            if filter_manufacturer > 0:
                query = query.filter(Asset.manufacturers.any(id=filter_manufacturer))
            
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
            asset_infos = {str(asset.id): asset for asset in assets}
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
    
    # Asset-Daten für Anzeige vorbereiten
    asset_infos = {str(asset.id): asset for asset in assets}
    
    # Vorlagen laden - nur die, die zum ausgewählten Lieferanten passen
    templates = OrderTemplate.query.filter_by(supplier_id=supplier_id).all()
    
    # An dieser Stelle keine weitere Vorlage laden, da dies jetzt direkt
    # in der POST-Verarbeitung mit dem 'load_template'-Action passiert
    
    return render_template(
        'order/wizard/step2_articles.html',
        form=form,
        supplier=supplier,
        location=location,
        asset_infos=asset_infos,
        categories=categories,
        templates=templates
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
    
    return render_template(
        'order/wizard/step3_details.html',
        form=form,
        supplier=supplier,
        location=location,
        selected_items=selected_items
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
                # Hinweis: Der Asset-Import erfolgt automatisch durch einen Trigger/Handler, der auf den Status 'erledigt' reagiert
                # Gemäß der Erinnerung vom 19.04.2025 funktioniert dieser Workflow bereits zuverlässig
                print(f"DEBUG: Asset-Import für Bestellung #{new_order.id} wurde ausgelöst durch Status 'erledigt'")
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
    
    return render_template(
        'order/wizard/step4_confirm.html',
        form=form,
        supplier=supplier,
        location=location,
        selected_items=selected_items,
        order_data=wizard_data,
        today=datetime.now()
    )

# Neuer Link in der Hauptnavigation zum Assistenten
@order.route('/wizard/start')
def start_wizard():
    """Startet den Bestellassistenten"""
    _reset_wizard_session()
    return redirect(url_for('order.wizard_step1'))
