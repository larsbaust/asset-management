from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.models import Asset, Supplier, Order, OrderItem, Location, OrderTemplate, OrderTemplateItem
from app import db
from app.order.forms import WizardStep1Form, WizardStep2Form, WizardStep3Form, WizardStep4Form, AssetOrderForm
from app.order.wizard_routes import send_order_email  # reuse existing email helper
from app.order.order_utils import import_assets_from_order  # reuse import logic
# Optional: Tracking helpers (used to compute status badges similar to legacy overview)
try:
    from app.aftership_tracking import get_tracking_status, add_tracking_number  # type: ignore
except Exception:
    get_tracking_status = None  # Fallback if not available
    add_tracking_number = None

# MD3 Order Blueprint
md3_order_bp = Blueprint('md3_order', __name__, url_prefix='/md3/order')

# Wizard Session Key (reuse legacy key for continuity)
WIZARD_SESSION_KEY = 'order_wizard_data'


def _init_wizard_session():
    if WIZARD_SESSION_KEY not in session:
        session[WIZARD_SESSION_KEY] = {
            'supplier_id': None,
            'location_id': 0,
            'items': [],  # [{asset_id, quantity, serial_number}]
            'tracking_number': '',
            'tracking_carrier': '',
            'expected_delivery_date': '',  # ISO string 'YYYY-MM-DD'
            'comment': '',
        }
        session.modified = True


def _reset_wizard_session(keep_supplier_location: bool = False):
    if WIZARD_SESSION_KEY not in session:
        _init_wizard_session()
    base = session[WIZARD_SESSION_KEY]
    supplier_id = base.get('supplier_id')
    location_id = base.get('location_id')
    session[WIZARD_SESSION_KEY] = {
        'supplier_id': supplier_id if keep_supplier_location else None,
        'location_id': location_id if keep_supplier_location else 0,
        'items': [],
        'tracking_number': '',
        'tracking_carrier': '',
        'expected_delivery_date': '',
        'comment': '',
    }
    session.modified = True


def _update_wizard_session(key, value):
    if WIZARD_SESSION_KEY not in session:
        _init_wizard_session()
    session[WIZARD_SESSION_KEY][key] = value
    session.modified = True


def _get_wizard_session(key=None):
    if WIZARD_SESSION_KEY not in session:
        _init_wizard_session()
    if key is None:
        return session[WIZARD_SESSION_KEY]
    return session[WIZARD_SESSION_KEY].get(key)


def _tracking_status_class(tag: str | None) -> str:
    if tag == "Delivered":
        return "status-delivered"
    elif tag in ["InTransit", "OutForDelivery", "InfoReceived"]:
        return "status-intransit"
    elif tag in ["Exception", "Expired", "FailedAttempt"]:
        return "status-problem"
    else:
        return "status-unknown"


@md3_order_bp.route('/overview')
def overview():
    """MD3 Bestellübersicht (parallele MD3-Ansicht zur bestehenden /order/overview)."""
    show_archived = request.args.get('archived', type=int, default=0)

    query = Order.query
    query = query.filter(Order.archived == bool(show_archived))

    selected_status = request.args.get('status', '')
    if selected_status:
        query = query.filter(Order.status == selected_status)

    selected_supplier_id = request.args.get('supplier_id', type=int)
    if selected_supplier_id:
        query = query.filter(Order.supplier_id == selected_supplier_id)

    selected_location = request.args.get('location', '')
    if selected_location:
        # legacy field name: 'location' on Order can be a string field
        try:
            query = query.filter(Order.location == selected_location)
        except Exception:
            pass

    selected_tracking_number = request.args.get('tracking_number', '').strip()
    if selected_tracking_number:
        try:
            query = query.filter(Order.tracking_number.ilike(f"%{selected_tracking_number}%"))
        except Exception:
            pass

    orders = query.order_by(Order.order_date.desc()).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()

    # Locations used across orders (string-based)
    try:
        locations = sorted(set([
            o.location for o in Order.query.filter(Order.location != None).all()
            if getattr(o, 'location', None) and o.location.strip() != ''
        ]))
    except Exception:
        locations = []

    order_status_classes: dict[int, str] = {}
    for order in orders:
        tag = None
        subtag_message = None
        if getattr(order, 'tracking_number', None) and getattr(order, 'tracking_carrier', None) and get_tracking_status:
            try:
                tracking_info = get_tracking_status(order.tracking_number, order.tracking_carrier)  # type: ignore
            except Exception as e:
                tracking_info = None
                if "404" in str(e) and add_tracking_number:
                    try:
                        add_tracking_number(order.tracking_number, order.tracking_carrier)  # type: ignore
                        tracking_info = get_tracking_status(order.tracking_number, order.tracking_carrier)  # type: ignore
                    except Exception:
                        tracking_info = None
            if tracking_info and 'data' in tracking_info and 'tracking' in tracking_info['data']:
                tag = tracking_info['data']['tracking'].get('tag')
                subtag_message = tracking_info['data']['tracking'].get('subtag_message')
        # attach for template convenience
        order.tracking_tag = tag
        order.tracking_subtag_message = subtag_message
        order_status_classes[order.id] = _tracking_status_class(tag)

    return render_template(
        'md3/order/overview.html',
        orders=orders,
        suppliers=suppliers,
        locations=locations,
        show_archived=show_archived,
        selected_status=selected_status,
        selected_supplier_id=selected_supplier_id,
        selected_location=selected_location,
        selected_tracking_number=selected_tracking_number,
        order_status_classes=order_status_classes,
    )


@md3_order_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_csv():
    """MD3 CSV-Import für Bestellungen (parallele MD3-Ansicht)."""
    app_fields = ['Artikelnummer','Bezeichnung','Menge','Kategorie','Hersteller','Trackingnummer','Kommentar']
    preview_rows = None
    columns = []
    mapping = None
    import_result = None
    csv_text = None

    import io, csv as _csv
    try:
        import pandas as pd  # type: ignore
    except Exception:
        pd = None  # type: ignore

    if request.method == 'POST':
        if 'csvFile' in request.files and request.files['csvFile']:
            # Upload-Phase: Datei einlesen und Vorschau generieren
            file = request.files['csvFile']
            csv_text = file.read().decode('utf-8')
            if pd is not None:
                df = pd.read_csv(io.StringIO(csv_text), sep=None, engine='python')  # type: ignore
                columns = list(df.columns)
                preview_rows = df.head(10).values.tolist()
            else:
                sample = csv_text[:1024]
                delimiter = ';' if ';' in sample else ','
                reader = _csv.reader(io.StringIO(csv_text), delimiter=delimiter)
                rows = list(reader)
                columns = rows[0] if rows else []
                preview_rows = rows[1:11]
        elif 'csv_text' in request.form:
            # Mapping-Phase: Mapping übernehmen und (später) importieren
            csv_text = request.form['csv_text']
            mapping = {field: request.form.get(f'mapping_{field}') for field in app_fields}
            # TODO: Echten Import implementieren (hier nur Demo-Rückmeldung)
            import_result = f"Import erfolgreich! Mapping: {mapping}"

    return render_template(
        'md3/order/import.html',
        preview_rows=preview_rows,
        app_fields=app_fields,
        columns=columns,
        mapping=mapping,
        csv_text=csv_text,
        import_result=import_result
    )


# ===== MD3 Wizard (Bestellassistent) =====

@md3_order_bp.route('/wizard/start')
@login_required
def wizard_start():
    """Startet den MD3-Bestellassistenten (Schritt 1)."""
    _reset_wizard_session()
    return redirect(url_for('md3_order.wizard_step1'))


@md3_order_bp.route('/wizard/step1', methods=['GET', 'POST'])
@login_required
def wizard_step1():
    _init_wizard_session()
    suppliers = Supplier.query.order_by(Supplier.name).all()
    # Location is optional via Order.location_id; use Location model if available
    try:
        from app.models import Location
        locations = Location.query.order_by(Location.name).all()
    except Exception:
        locations = []

    form = WizardStep1Form()
    # "Alle Lieferanten" Option (ID -1) für Preisvergleich - 0 wird als "leer" interpretiert
    form.supplier_id.choices = [(-1, '🔍 Alle Lieferanten (Preisvergleich)')] + [(s.id, s.name) for s in suppliers]
    form.location.choices = [(0, '-- Kein Standort --')] + [(l.id, l.name) for l in locations]

    if request.method == 'GET' and request.args.get('supplier_id'):
        try:
            supplier_id = int(request.args.get('supplier_id'))
            if any(s.id == supplier_id for s in suppliers):
                form.supplier_id.data = supplier_id
                _update_wizard_session('supplier_id', supplier_id)
        except (ValueError, TypeError):
            pass

    if form.validate_on_submit():
        _update_wizard_session('supplier_id', form.supplier_id.data)
        _update_wizard_session('location_id', form.location.data if form.location.data else 0)
        _update_wizard_session('budget', float(form.budget.data) if form.budget.data else None)
        return redirect(url_for('md3_order.wizard_step2'))
    
    # Debug: Show validation errors
    if request.method == 'POST' and form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')

    return render_template('md3/order/wizard/step1.html', form=form, suppliers=suppliers)


@md3_order_bp.route('/wizard/step2', methods=['GET', 'POST'])
@login_required
def wizard_step2():
    data = _get_wizard_session()
    supplier_id = data.get('supplier_id')
    if supplier_id is None:
        flash('Bitte zuerst Schritt 1 abschließen.', 'warning')
        return redirect(url_for('md3_order.wizard_step1'))

    # Lade Bestellvorlagen
    from app.models import OrderTemplate
    if supplier_id == -1:
        # Alle Lieferanten - lade alle Vorlagen
        templates = OrderTemplate.query.order_by(OrderTemplate.name).all()
    else:
        # Spezifischer Lieferant
        templates = OrderTemplate.query.filter_by(supplier_id=supplier_id).order_by(OrderTemplate.name).all()
    
    # Budget aus Session holen
    budget = data.get('budget')

    form = WizardStep2Form()

    # Populate select choices to satisfy WTForms validation
    try:
        from app.models import Category, Manufacturer, Supplier
        form.filter_category.choices = [(0, 'Alle Kategorien')] + [
            (c.id, c.name) for c in Category.query.order_by(Category.name).all()
        ]
        form.filter_manufacturer.choices = [(0, 'Alle Hersteller')] + [
            (m.id, m.name) for m in Manufacturer.query.order_by(Manufacturer.name).all()
        ]
        form.filter_supplier.choices = [(0, 'Alle Lieferanten')] + [
            (s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()
        ]
    except Exception:
        form.filter_category.choices = [(0, 'Alle Kategorien')]
        form.filter_manufacturer.choices = [(0, 'Alle Hersteller')]
        form.filter_supplier.choices = [(0, 'Alle Lieferanten')]

    # Build asset list based on filters
    query = Asset.query.filter(Asset.status == 'active')
    # Restrict to assets that have the chosen supplier (nur wenn nicht "Alle")
    if supplier_id != -1:
        try:
            query = query.filter(Asset.suppliers.any(Supplier.id == supplier_id))
        except Exception:
            pass

    # Apply filters
    if request.method == 'POST':
        name = form.filter_name.data or ''
        if name.strip():
            try:
                from sqlalchemy import or_
                query = query.filter(Asset.name.ilike(f"%{name}%"))
            except Exception:
                pass
        if form.filter_category.data and int(form.filter_category.data) != 0:
            try:
                query = query.filter(Asset.category_id == int(form.filter_category.data))
            except Exception:
                pass
        if form.filter_manufacturer.data and int(form.filter_manufacturer.data) != 0:
            try:
                # manufacturer m2m
                from app.models import Manufacturer
                query = query.filter(Asset.manufacturers.any(Manufacturer.id == int(form.filter_manufacturer.data)))
            except Exception:
                pass
        if form.filter_supplier.data and int(form.filter_supplier.data) != 0:
            try:
                # supplier m2m
                from app.models import Supplier
                query = query.filter(Asset.suppliers.any(Supplier.id == int(form.filter_supplier.data)))
            except Exception:
                pass
    
    assets = query.order_by(Asset.name).limit(100).all()

    # ✅ Check für OCI-importierte Assets
    oci_asset_ids = session.get('oci_asset_ids', [])
    oci_supplier_name = session.get('oci_supplier', None)
    
    # Markiere OCI-Assets (für Highlighting im Template)
    for asset in assets:
        asset.is_oci_import = asset.id in oci_asset_ids

    # Populate FieldList on GET
    if request.method == 'GET':
        form.assets.entries = []
        for a in assets:
            entry = AssetOrderForm()
            entry.asset_id.data = str(a.id)
            entry.quantity.data = 1
            entry.select.data = False
            form.assets.append_entry(entry.data)

    # If user clicked filter, rebuild entries for the filtered list and render
    if request.method == 'POST' and 'filter' in request.form:
        form.assets.entries = []
        for a in assets:
            entry = AssetOrderForm()
            entry.asset_id.data = str(a.id)
            entry.quantity.data = 1
            entry.select.data = False
            form.assets.append_entry(entry.data)
        return render_template('md3/order/wizard/step2.html', 
                             form=form, assets=assets, templates=templates, 
                             supplier_id=supplier_id, budget=budget,
                             oci_asset_ids=oci_asset_ids, oci_supplier_name=oci_supplier_name)

    if form.validate_on_submit():
        selected = []
        for subform in form.assets:
            try:
                if subform.select.data:
                    selected.append({
                        'asset_id': int(subform.asset_id.data),
                        'quantity': int(subform.quantity.data or 1),
                        'serial_number': (subform.serial_number.data or '').strip()
                    })
            except Exception:
                continue
        if not selected:
            flash('Bitte mindestens einen Artikel auswählen.', 'warning')
        else:
            _update_wizard_session('items', selected)
            # ✅ Clear OCI session after successful selection
            session.pop('oci_asset_ids', None)
            session.pop('oci_supplier', None)
            return redirect(url_for('md3_order.wizard_step3'))

    return render_template('md3/order/wizard/step2.html', 
                         form=form, assets=assets, templates=templates, 
                         supplier_id=supplier_id, budget=budget,
                         oci_asset_ids=oci_asset_ids, oci_supplier_name=oci_supplier_name)


@md3_order_bp.route('/wizard/step3', methods=['GET', 'POST'])
@login_required
def wizard_step3():
    data = _get_wizard_session()
    if not data.get('items'):
        flash('Bitte zuerst Schritt 2 abschließen.', 'warning')
        return redirect(url_for('md3_order.wizard_step2'))

    form = WizardStep3Form()

    if request.method == 'GET':
        form.tracking_number.data = data.get('tracking_number', '')
        form.tracking_carrier.data = data.get('tracking_carrier', '')
        # expected_delivery_date is ISO string in session
        # WTForms DateField will display None gracefully
        form.comment.data = data.get('comment', '')

    if form.validate_on_submit():
        _update_wizard_session('tracking_number', form.tracking_number.data or '')
        _update_wizard_session('tracking_carrier', form.tracking_carrier.data or '')
        # Store date as ISO string to keep session JSON-safe
        iso_date = ''
        try:
            if form.expected_delivery_date.data:
                iso_date = form.expected_delivery_date.data.isoformat()
        except Exception:
            iso_date = ''
        _update_wizard_session('expected_delivery_date', iso_date)
        _update_wizard_session('comment', form.comment.data or '')
        return redirect(url_for('md3_order.wizard_step4'))

    return render_template('md3/order/wizard/step3.html', form=form)


@md3_order_bp.route('/wizard/step4', methods=['GET', 'POST'])
@login_required
def wizard_step4():
    data = _get_wizard_session()
    if not data.get('items'):
        flash('Keine Artikel ausgewählt.', 'warning')
        return redirect(url_for('md3_order.wizard_step2'))

    # Load supplier and location display
    supplier = Supplier.query.get(data.get('supplier_id')) if data.get('supplier_id') else None
    location_obj = None
    try:
        from app.models import Location
        if data.get('location_id'):
            location_obj = Location.query.get(int(data.get('location_id')))
    except Exception:
        pass

    # Build item details for summary
    item_details = []
    for it in data.get('items', []):
        a = Asset.query.get(it['asset_id'])
        if not a:
            continue
        item_details.append({
            'asset': a,
            'quantity': it.get('quantity', 1),
            'serial_number': it.get('serial_number', '')
        })

    form = WizardStep4Form()

    if form.validate_on_submit():
        # Create order and items
        order = Order(
            supplier_id=data.get('supplier_id'),
            status='offen',
            comment=data.get('comment') or '',
            tracking_number=data.get('tracking_number') or '',
            tracking_carrier=data.get('tracking_carrier') or '',
        )
        # Location handling
        loc_id = data.get('location_id')
        try:
            loc_id = int(loc_id) if loc_id is not None else 0
        except Exception:
            loc_id = 0
        order.location_id = loc_id if loc_id else None

        # Expected delivery date
        from datetime import datetime
        iso = data.get('expected_delivery_date')
        if iso:
            try:
                order.expected_delivery_date = datetime.fromisoformat(iso)
            except Exception:
                pass

        db.session.add(order)
        db.session.flush()  # get order.id

        for it in data.get('items', []):
            oi = OrderItem(
                order_id=order.id,
                asset_id=int(it['asset_id']),
                quantity=int(it.get('quantity', 1) or 1),
                serial_number=(it.get('serial_number') or None)
            )
            db.session.add(oi)

        # Determine action
        action = 'save'
        if form.send_email.data:
            action = 'send_email'
        elif form.import_assets.data:
            action = 'import_assets'

        # Apply action
        if action == 'import_assets':
            order.status = 'erledigt'
        db.session.commit()

        # KALENDER-EVENT für Liefertermin erstellen
        if order.expected_delivery_date:
            from app.models import CalendarEvent, EVENT_TYPE_DELIVERY, EVENT_STATUS_PLANNED
            from flask_login import current_user
            
            # Titel mit Lieferantenname
            supplier_name = supplier.name if supplier else 'Unbekannter Lieferant'
            event_title = f"Lieferung: Bestellung #{order.id}"
            event_description = f"Erwartete Lieferung von {supplier_name}"
            
            # Artikel-Details hinzufügen
            if data.get('items'):
                item_count = len(data.get('items', []))
                event_description += f"\n{item_count} Artikel"
            
            calendar_event = CalendarEvent(
                title=event_title,
                description=event_description,
                start_datetime=order.expected_delivery_date,
                event_type=EVENT_TYPE_DELIVERY,
                status=EVENT_STATUS_PLANNED,
                order_id=order.id,
                created_by_id=current_user.id if current_user.is_authenticated else None
            )
            db.session.add(calendar_event)
            db.session.commit()
            print(f"DEBUG: Kalender-Event #{calendar_event.id} für Bestellung #{order.id} erstellt")

        # AUTOMATISCHER ASSET-IMPORT für alle Bestellungen mit Status 'erledigt'
        if order.status == 'erledigt':
            # Expliziter Aufruf des Asset-Imports für ALLE Bestellungen mit Status 'erledigt'
            created_assets, skipped_items = import_assets_from_order(order)
            print(f"DEBUG: MD3 Asset-Import für Bestellung #{order.id} wurde automatisch ausgelöst - {len(created_assets)} Assets erstellt")

        # Side effects after commit
        try:
            if action == 'send_email':
                ok = send_order_email(order.id)
                if not ok:
                    flash('Bestellung gespeichert, aber E-Mail-Versand fehlgeschlagen.', 'warning')
        except Exception:
            # Fail gracefully, order was created
            flash('Bestellung gespeichert, Nebenaktion teilweise fehlgeschlagen.', 'warning')

        _reset_wizard_session()
        if action == 'import_assets':
            flash(f'Bestellung #{order.id} gespeichert und Assets importiert.', 'success')
            # Redirect to MD3 Assets page
            return redirect('/md3/assets')
        elif action == 'send_email':
            flash(f'Bestellung #{order.id} gespeichert und E-Mail gesendet.', 'success')
        else:
            flash(f'Bestellung #{order.id} wurde erstellt.', 'success')
        return redirect(url_for('md3_order.overview'))

    return render_template(
        'md3/order/wizard/step4.html',
        supplier=supplier,
        location=location_obj,
        items=item_details,
        data=data,
        form=form,
    )


# ========================
# API Routes für Bestellvorlagen
# ========================

@md3_order_bp.route('/api/order-template/<int:template_id>', methods=['GET'])
@login_required
def get_order_template(template_id):
    """API: Bestellvorlage laden"""
    try:
        template = OrderTemplate.query.get_or_404(template_id)
        
        # Template-Items laden
        items = []
        for item in template.items:
            items.append({
                'asset_id': item.asset_id,
                'quantity': item.quantity
            })
        
        return jsonify({
            'success': True,
            'template_id': template.id,
            'name': template.name,
            'supplier_id': template.supplier_id,
            'items': items
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@md3_order_bp.route('/api/order-template/save', methods=['POST'])
@login_required
def save_order_template():
    """API: Neue Bestellvorlage speichern"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
        
        if not data.get('items') or len(data['items']) == 0:
            return jsonify({'success': False, 'message': 'Mindestens ein Artikel erforderlich'}), 400
        
        # Neue Vorlage erstellen
        template = OrderTemplate(
            name=data['name'],
            supplier_id=data.get('supplier_id'),
            location_id=None  # Optional: könnte auch aus Session kommen
        )
        db.session.add(template)
        db.session.flush()  # Um template.id zu erhalten
        
        # Items hinzufügen
        for item_data in data['items']:
            item = OrderTemplateItem(
                template_id=template.id,
                asset_id=int(item_data['asset_id']),
                quantity=int(item_data.get('quantity', 1))
            )
            db.session.add(item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'template_id': template.id,
            'message': 'Vorlage erfolgreich gespeichert'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
