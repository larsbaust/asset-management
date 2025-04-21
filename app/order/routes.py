from flask import render_template, request, redirect, url_for, flash
from app.order import order
from app.models import Supplier, Asset, Order, OrderItem
from app import db
from app.order.forms import OrderPlanForm, AssetOrderForm

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
        order = Order(
            supplier_id=form.supplier.data,
            location_id=form.location.data,
            tracking_number=form.tracking_number.data.strip() if form.tracking_number.data else None
        )
        db.session.add(order)
        db.session.flush()  # order.id verfügbar
        n_items = 0
        for asset_form in form.assets:
            if asset_form.select.data and asset_form.quantity.data > 0:
                order_item = OrderItem(
                    order_id=order.id,
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
    db.session.delete(order)
    db.session.commit()
    flash('Bestellung wurde gelöscht.', 'danger')
    args = request.args.to_dict()
    # Nach Löschen ins Archiv zurück, falls dort gelöscht wurde
    return redirect(url_for('order.order_overview', **args))

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
    return render_template('order/overview.html', orders=orders, suppliers=suppliers, locations=locations, show_archived=show_archived, selected_status=selected_status, selected_supplier_id=selected_supplier_id, selected_location=selected_location, selected_tracking_number=selected_tracking_number)

@order.route('/order/<int:order_id>/export')
def order_export(order_id):
    order = Order.query.get_or_404(order_id)
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
    form = OrderEditForm(obj=order)
    import sqlalchemy
    from app.models import Asset
    status_before = order.status
    if form.validate_on_submit():
        order.status = form.status.data
        order.comment = form.comment.data
        db.session.commit()
        # Automatischer Asset-Import bei Statuswechsel auf 'erledigt'
        if status_before != 'erledigt' and order.status == 'erledigt':
            created_assets = []
            skipped_items = []
            for item in order.items:
                serial_number = (item.serial_number or '').strip() if hasattr(item, 'serial_number') else ''
                # Prüfen, ob Asset mit dieser Seriennummer existiert
                asset_exists = False
                if serial_number:
                    asset_exists = Asset.query.filter_by(serial_number=serial_number).first() is not None
                if not asset_exists:
                    # Gemeinsame Felder übernehmen
                    asset_data = {}
                    for field in ['name', 'category_id', 'manufacturer_id', 'ean', 'serial_number', 'comment']:
                        # Feld im OrderItem, sonst aus Asset übernehmen
                        value = getattr(item, field, None)
                        if not value and hasattr(item, 'asset') and item.asset is not None:
                            # Mapping: OrderItem.name -> item.asset.name usw.
                            if field == 'name':
                                value = getattr(item.asset, 'name', None)
                            elif field == 'category_id':
                                value = getattr(item.asset, 'category_id', None)
                            elif field == 'manufacturer_id':
                                value = getattr(item.asset, 'manufacturer_id', None)
                            elif field == 'ean':
                                value = getattr(item.asset, 'ean', None)
                        if value:
                            asset_data[field] = value
                    asset_data['location'] = order.location if hasattr(order, 'location') else None
                    # Prüfen, ob Name gesetzt ist (direkt oder über Asset)
                    asset_name = asset_data.get('name', None)
                    if asset_name and str(asset_name).strip():
                        new_asset = Asset(**asset_data)
                        db.session.add(new_asset)
                        created_assets.append(new_asset)
                    else:
                        skipped_items.append(item)
            db.session.commit()
            msg = f'{len(created_assets)} neue Assets wurden automatisch aus der Bestellung angelegt.' if created_assets else ''
            if skipped_items:
                msg += f' {len(skipped_items)} Position(en) wurden übersprungen, da kein Name gesetzt war.'
            if msg:
                flash(msg.strip(), 'warning' if skipped_items else 'success')
            db.session.commit()
            if created_assets:
                flash(f'{len(created_assets)} neue Assets wurden automatisch aus der Bestellung angelegt.', 'success')
            else:
                flash('Keine neuen Assets angelegt (Seriennummern bereits vorhanden oder leer).', 'info')
        flash('Bestellstatus und Kommentar aktualisiert!')
        return redirect(url_for('order.order_detail', order_id=order.id))
    return render_template('order/detail.html', order=order, form=form)

@order.route('/order/history')
def order_history():
    return render_template('order/history.html')
