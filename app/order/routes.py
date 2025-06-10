from flask import render_template, request, redirect, url_for, flash
from app.order import order
from app.models import Supplier, Asset, Order, OrderItem
from app import db
from app.order.forms import OrderPlanForm, AssetOrderForm
from flask_mail import Message
from app import mail
from datetime import datetime
from app.order.order_utils import import_assets_from_order

@order.route('/order/<int:order_id>/send_email')
def send_order_email(order_id):
    order_obj = Order.query.get_or_404(order_id)
    supplier = order_obj.supplier
    if not supplier.email:
        flash('Lieferant hat keine E-Mail-Adresse hinterlegt.', 'danger')
        return redirect(url_for('order.order_detail', order_id=order_id))
    html = render_template('order/order_email.html', order=order_obj, supplier=supplier)
    msg = Message(subject=f"Neue Bestellung #{order_obj.id}",
                  recipients=[supplier.email],
                  html=html,
                  sender="noreply@example.com")  # Passe den Absender ggf. an
    try:
        mail.send(msg)
        flash('Bestellung wurde per E-Mail an den Lieferanten gesendet.', 'success')
    except Exception as e:
        flash(f'Fehler beim Senden der E-Mail: {e}', 'danger')
    return redirect(url_for('order.order_detail', order_id=order_id))

@order.route('/order/plan', methods=['GET', 'POST'])
def order_plan():
    suppliers = Supplier.query.all()
    form = OrderPlanForm(request.form if request.method == 'POST' else None)
    form.supplier.choices = [(s.id, s.name) for s in suppliers]

    # Filterwerte aus Form holen
    filter_name = form.filter_name.data or ''
    filter_category = form.filter_category.data or 0
    filter_manufacturer = form.filter_manufacturer.data or 0
    filter_assignment = form.filter_assignment.data or 0

    # Query für Assets aufbauen
    assets_query = Asset.query
    if filter_name:
        assets_query = assets_query.filter(Asset.name.ilike(f"%{filter_name}%"))
    if filter_category and int(filter_category) != 0:
        assets_query = assets_query.filter(Asset.category_id == int(filter_category))
    if filter_manufacturer and int(filter_manufacturer) != 0:
        assets_query = assets_query.filter(Asset.manufacturers.any(id=int(filter_manufacturer)))
    if filter_assignment and int(filter_assignment) != 0:
        assets_query = assets_query.filter(Asset.assignments.any(id=int(filter_assignment)))
    assets = assets_query.all()

    # FieldList mit allen Assets befüllen (bei GET und POST, damit die Struktur stimmt)
    if request.method == 'GET' or not form.assets.entries or len(form.assets.entries) != len(assets):
        form.assets.entries = []
        for asset in assets:
            asset_form = AssetOrderForm()
            asset_form.asset_id.data = asset.id
            asset_form.select.data = False
            asset_form.quantity.data = 1
            form.assets.append_entry(asset_form.data)
    else:
        # Beim POST sicherstellen, dass asset_id gesetzt ist
        for i, asset in enumerate(assets):
            if i < len(form.assets.entries):
                form.assets.entries[i].asset_id.data = asset.id
    if form.validate_on_submit():
        # Bestellung anlegen
        new_order = Order(
            supplier_id=form.supplier.data,
            location_id=form.location.data if form.location.data != 0 else None,
            tracking_number=form.tracking_number.data,
            tracking_carrier=form.tracking_carrier.data,
            comment=form.comment.data,
            order_date=datetime.utcnow(),
            status='offen',
            archived=False
        )
        db.session.add(new_order)
        db.session.flush()  # order.id verfügbar
        n_items = 0
        for asset_form in form.assets:
            if asset_form.select.data and asset_form.quantity.data > 0:
                order_item = OrderItem(
                    order_id=new_order.id,
                    asset_id=int(asset_form.asset_id.data),
                    quantity=asset_form.quantity.data,
                    serial_number=asset_form.serial_number.data.strip() if asset_form.serial_number.data else None
                )
                db.session.add(order_item)
                n_items += 1
        db.session.commit()
        if n_items > 0:
            flash('Bestellung erfolgreich geplant!')
            return redirect(url_for('order.order_overview'))
        else:
            flash('Bitte wähle mindestens ein Asset aus.', 'warning')
    elif request.method == 'POST':
        flash('Formular ungültig. Prüfe die Eingaben.', 'danger')
        print('Formularfehler:', form.errors)
    asset_infos = {str(asset.id): asset for asset in assets}
    # Filterwerte für das Template bereitstellen
    selected_filters = {
        'filter_name': filter_name,
        'filter_category': int(filter_category),
        'filter_manufacturer': int(filter_manufacturer),
        'filter_assignment': int(filter_assignment)
    }
    return render_template('order/plan.html', form=form, asset_infos=asset_infos, selected_filters=selected_filters)


from flask import Response, request

@order.route('/order/<int:order_id>/archive', methods=['POST'])
def archive_order(order_id):
    from flask import request, redirect, url_for, flash
    order = Order.query.get_or_404(order_id)
    print(f"[DEBUG] Order-Export-Dialog für Order-ID: {order_id}, Items: {order.items}")
    if not order.archived:
        order.archived = True
        db.session.commit()
        flash('Bestellung wurde archiviert.', 'info')
    else:
        flash('Bestellung ist bereits archiviert.', 'warning')
    args = request.args.to_dict()
    return redirect(url_for('order.order_overview', **args))

@order.route('/order/<int:order_id>/restore', methods=['POST'])
def restore_order(order_id):
    from flask import request, redirect, url_for, flash
    order = Order.query.get_or_404(order_id)
    print(f"[DEBUG] Order-Export-Dialog für Order-ID: {order_id}, Items: {order.items}")
    if order.archived:
        order.archived = False
        db.session.commit()
        flash('Bestellung wurde wiederhergestellt.', 'success')
    else:
        flash('Bestellung ist nicht archiviert.', 'warning')
    args = request.args.to_dict()
    return redirect(url_for('order.order_overview', archived=1, **args))

@order.route('/order/<int:order_id>/delete', methods=['POST'])
def delete_order(order_id):
    from flask import request, redirect, url_for, flash
    order = Order.query.get_or_404(order_id)
    print(f"[DEBUG] Order-Export-Dialog für Order-ID: {order_id}, Items: {order.items}")
    db.session.delete(order)
    db.session.commit()
    flash('Bestellung wurde gelöscht.', 'danger')
    args = request.args.to_dict()
    # Nach Löschen ins Archiv zurück, falls dort gelöscht wurde
    return redirect(url_for('order.order_overview', **args))

def tracking_status_class(tag):
    if tag == "Delivered":
        return "status-delivered"
    elif tag in ["InTransit", "OutForDelivery", "InfoReceived"]:
        return "status-intransit"
    elif tag in ["Exception", "Expired", "FailedAttempt"]:
        return "status-problem"
    else:
        return "status-unknown"
 

from flask import Response, request, render_template
import csv
from io import StringIO

@order.route('/order/overview')
def order_overview():
    show_archived = request.args.get('archived', type=int, default=0)
    query = Order.query
    # Filter nach archiviert/aktiv
    if show_archived:
        query = query.filter(Order.archived == True)
    else:
        query = query.filter(Order.archived == False)
    # Filter Status
    selected_status = request.args.get('status', '')
    if selected_status:
        query = query.filter(Order.status == selected_status)
    # Filter Lieferant
    selected_supplier_id = request.args.get('supplier_id', type=int)
    if selected_supplier_id:
        query = query.filter(Order.supplier_id == selected_supplier_id)
    # Filter Standort
    selected_location = request.args.get('location', '')
    if selected_location:
        query = query.filter(Order.location == selected_location)
    # Filter Trackingnummer (Freitext, Teilstring)
    selected_tracking_number = request.args.get('tracking_number', '').strip()
    if selected_tracking_number:
        query = query.filter(Order.tracking_number.ilike(f"%{selected_tracking_number}%"))
    orders = query.order_by(Order.order_date.desc()).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()
    # Alle Standorte für Dropdown (nur die, die in Orders verwendet werden)
    locations = sorted(set([o.location for o in Order.query.filter(Order.location != None).all() if o.location and o.location.strip() != '']))
    # Mapping: Tracking-Status-Klasse für jede Bestellung
    from app.aftership_tracking import get_tracking_status, add_tracking_number
    order_status_classes = {}
    for order in orders:
        tag = None
        if order.tracking_number and order.tracking_carrier:
            try:
                tracking_info = get_tracking_status(order.tracking_number, order.tracking_carrier)
                print(f"[TrackingMore] tracking_info für Order {order.id}: {tracking_info}")
            except Exception as e:
                tracking_info = None
                if "404" in str(e):
                    # Trackingnummer registrieren und erneut abfragen
                    result = add_tracking_number(order.tracking_number, order.tracking_carrier)
                    print(f"[TrackingMore] add_tracking_number({order.tracking_number}, {order.tracking_carrier}) response:", result)
                    try:
                        tracking_info = get_tracking_status(order.tracking_number, order.tracking_carrier)
                        print(f"[TrackingMore] get_tracking_status after add_tracking_number response:", tracking_info)
                    except Exception as e2:
                        print(f"[TrackingMore] get_tracking_status after add_tracking_number: {e2}")
                        tracking_info = None
            tag = None
            subtag_message = None
            # AfterShip Antwort korrekt auswerten
            if tracking_info and 'data' in tracking_info and 'tracking' in tracking_info['data']:
                tag = tracking_info['data']['tracking'].get('tag')
                subtag_message = tracking_info['data']['tracking'].get('subtag_message')
            print(f"[AfterShip] tag für Order {order.id}: {tag}")
            print(f"[AfterShip] subtag_message für Order {order.id}: {subtag_message}")
            order.tracking_tag = tag
            order.tracking_subtag_message = subtag_message
        else:
            order.tracking_tag = None
            order.tracking_subtag_message = None
        order_status_classes[order.id] = tracking_status_class(order.tracking_tag) if order.tracking_tag else "status-unknown"
        print(f"[TrackingMore] order_status_classes für Order {order.id}: {order_status_classes[order.id]}")

    return render_template('order/overview.html', orders=orders, suppliers=suppliers, locations=locations, show_archived=show_archived, selected_status=selected_status, selected_supplier_id=selected_supplier_id, selected_location=selected_location, selected_tracking_number=selected_tracking_number, order_status_classes=order_status_classes)


@order.route('/order/<int:order_id>/export_dialog', methods=['GET', 'POST'])
def order_export_dialog(order_id):
    import datetime
    print("=== PREVIEW TEST ===", datetime.datetime.now(), dict(request.args), request.method)
    print(">>> ALLE REQUEST ARGS:", dict(request.args))
    print(">>> REQUEST METHOD:", request.method)
    order = Order.query.get_or_404(order_id)
    print(f"[DEBUG] Order-Export-Dialog für Order-ID: {order_id}, Items: {order.items}")
    # Verfügbare Felder (kann beliebig erweitert werden)
    available_fields = [
        {'name': 'article_number', 'label': 'Artikelnummer', 'export_name': 'Artikelnummer', 'selected': True},
        {'name': 'name', 'label': 'Bezeichnung', 'export_name': 'Bezeichnung', 'selected': True},
        {'name': 'quantity', 'label': 'Menge', 'export_name': 'Menge', 'selected': True},
        {'name': 'category', 'label': 'Kategorie', 'export_name': 'Kategorie', 'selected': False},
        {'name': 'manufacturer', 'label': 'Hersteller', 'export_name': 'Hersteller', 'selected': True},
        {'name': 'tracking_number', 'label': 'Trackingnummer', 'export_name': 'Trackingnummer', 'selected': False},
        {'name': 'comment', 'label': 'Kommentar', 'export_name': 'Kommentar', 'selected': False},
    ]
    # Vorschau-API (AJAX):
    if request.args.get('preview') == '1':
        print('### PREVIEW-BRANCH WIRD AUSGEFÜHRT ###')
        from flask import jsonify
        # Felder aus Query-String übernehmen
        selected_fields = []
        for field in available_fields:
            if request.args.get(f'export_{field["name"]}') == '1':
                export_name = request.args.get(f'colname_{field["name"]}', field['export_name'])
                selected_fields.append({'name': field['name'], 'export_name': export_name})
        preview_rows = []
        for item in order.items[:5]:
            row = []
            for f in selected_fields:
                try:
                    if f['name'] == 'article_number':
                        row.append(getattr(item.asset, 'article_number', '') if item.asset else '')
                    elif f['name'] == 'name':
                        row.append(getattr(item.asset, 'name', '') if item.asset else '')
                    elif f['name'] == 'quantity':
                        row.append(getattr(item, 'quantity', ''))
                    elif f['name'] == 'category':
                        row.append(getattr(item.asset.category, 'name', '') if item.asset and getattr(item.asset, 'category', None) else '')
                    elif f['name'] == 'manufacturer':
                        # Robust: Hersteller kann fehlen oder nicht gesetzt sein
                        mans = getattr(item.asset, 'manufacturers', None) if item.asset else None
                        if mans:
                            row.append(', '.join([m.name for m in mans]))
                        else:
                            row.append('')
                    elif f['name'] == 'tracking_number':
                        row.append(order.tracking_number or '')
                    elif f['name'] == 'comment':
                        row.append(item.comment if hasattr(item, 'comment') else '')
                    else:
                        row.append('')
                except Exception as e:
                    row.append(f'Fehler: {e}')
            preview_rows.append(row)
        return jsonify({
            'header': [f['export_name'] for f in selected_fields],
            'rows': preview_rows,
            'only_empty': False
        })
    # POST = Export generieren
    if request.method == 'POST':
        # Mapping aus Formular übernehmen
        selected_fields = []
        for field in available_fields:
            if request.form.get(f'export_{field["name"]}'):
                export_name = request.form.get(f'colname_{field["name"]}', field['export_name'])
                selected_fields.append({'name': field['name'], 'export_name': export_name})
        # CSV generieren
        output = StringIO()
        writer = csv.writer(output, delimiter=';')
        # Kopfzeile
        writer.writerow([f['export_name'] for f in selected_fields])
        # Datenzeilen
        for item in order.items:
            row = []
            for f in selected_fields:
                if f['name'] == 'article_number':
                    row.append(item.asset.article_number if item.asset else '')
                elif f['name'] == 'name':
                    row.append(item.asset.name if item.asset else '')
                elif f['name'] == 'quantity':
                    row.append(item.quantity)
                elif f['name'] == 'category':
                    row.append(item.asset.category.name if item.asset and item.asset.category else '')
                elif f['name'] == 'manufacturer':
                    if item.asset and item.asset.manufacturers:
                        row.append(', '.join([m.name for m in item.asset.manufacturers]))
                    else:
                        row.append('')
                elif f['name'] == 'tracking_number':
                    row.append(order.tracking_number or '')
                elif f['name'] == 'comment':
                    row.append(item.comment if hasattr(item, 'comment') else '')
                else:
                    row.append('')
            writer.writerow(row)
        csv_data = output.getvalue()
        output.close()
        return Response(csv_data, mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename=order_{order.id}_custom.csv"})
    # GET: Dialog anzeigen
    return render_template('order/export_dialog.html', order=order, available_fields=available_fields)


# Die alte Einzelbestellungs-Exportfunktion bleibt erhalten
@order.route('/order/<int:order_id>/export')
def order_export(order_id):
    order = Order.query.get_or_404(order_id)
    print(f"[DEBUG] Order-Export-Dialog für Order-ID: {order_id}, Items: {order.items}")
    def generate():
        yield 'Bestellung ID;Lieferant;Datum;Status;Kommentar\n'
        yield f'{order.id};{order.supplier.name};{order.order_date.strftime("%d.%m.%Y %H:%M")};{order.status};{order.comment or ""}\n'
        yield '\nPositionen:\nAsset;Menge\n'
        for item in order.items:
            yield f'{item.asset.name};{item.quantity}\n'
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename=order_{order.id}.csv"})

from .forms import OrderEditForm

@order.route('/order/<int:order_id>', methods=['GET', 'POST'])
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    print(f"[DEBUG] Order-Export-Dialog für Order-ID: {order_id}, Items: {order.items}")
    form = OrderEditForm(obj=order)
    import sqlalchemy
    from app.models import Asset
    status_before = order.status
    if form.validate_on_submit():
        # Kommentar als OrderComment speichern
        if form.comment.data and form.comment.data.strip():
            from app.models import OrderComment
            new_comment = OrderComment(order_id=order.id, content=form.comment.data.strip())
            db.session.add(new_comment)
            db.session.commit()
            flash('Kommentar dokumentiert!', 'success')
            return redirect(url_for('order.order_detail', order_id=order.id))
        order.status = form.status.data
        order.tracking_number = form.tracking_number.data
        order.tracking_carrier = form.tracking_carrier.data
        order.comment = form.comment.data
        db.session.commit()
        # Automatischer Asset-Import bei Statuswechsel auf 'erledigt'
        if status_before != 'erledigt' and order.status == 'erledigt':
            # Import-Funktion aufrufen
            import_assets_from_order(order)
        flash('Bestellstatus und Kommentar aktualisiert!')
        return redirect(url_for('order.order_detail', order_id=order.id))
    from app.models import OrderComment
    return render_template('order/detail.html', order=order, form=form, OrderComment=OrderComment)

@order.route('/order/history')
def order_history():
    return render_template('order/history.html')
