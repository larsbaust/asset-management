from flask import render_template, request, redirect, url_for, flash
from app.order import order
from app.models import Supplier, Asset, Order, OrderItem
from app import db
from app.order.forms import OrderPlanForm, AssetOrderForm

@order.route('/order/plan', methods=['GET', 'POST'])
def order_plan():
    suppliers = Supplier.query.all()
    assets = Asset.query.all()
    form = OrderPlanForm()
    # Lieferanten-Auswahl befüllen
    form.supplier.choices = [(s.id, s.name) for s in suppliers]
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
        order = Order(supplier_id=form.supplier.data)
        db.session.add(order)
        db.session.flush()  # order.id verfügbar
        n_items = 0
        for asset_form in form.assets:
            if asset_form.select.data and asset_form.quantity.data > 0:
                order_item = OrderItem(order_id=order.id, asset_id=int(asset_form.asset_id.data), quantity=asset_form.quantity.data)
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
    # Asset-Daten für das Template (Name/Kategorie)
    asset_infos = {str(asset.id): asset for asset in assets}
    return render_template('order/plan.html', form=form, asset_infos=asset_infos)

from flask import Response, request

@order.route('/order/overview')
def order_overview():
    status = request.args.get('status', type=str)
    supplier_id = request.args.get('supplier_id', type=int)
    query = Order.query
    if status:
        query = query.filter(Order.status == status)
    if supplier_id:
        query = query.filter(Order.supplier_id == supplier_id)
    orders = query.order_by(Order.order_date.desc()).all()
    suppliers = Supplier.query.all()
    return render_template('order/overview.html', orders=orders, suppliers=suppliers, selected_status=status, selected_supplier_id=supplier_id)

@order.route('/order/<int:order_id>/export')
def order_export(order_id):
    order = Order.query.get_or_404(order_id)
    def generate():
        yield 'Bestellung ID;Lieferant;Datum;Status;Kommentar\n'
        yield f'{order.id};{order.supplier.name};{order.order_date.strftime('%d.%m.%Y %H:%M')};{order.status};{order.comment or ''}\n'
        yield '\nPositionen:\nAsset;Menge\n'
        for item in order.items:
            yield f'{item.asset.name};{item.quantity}\n'
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename=order_{order.id}.csv"})

from .forms import OrderEditForm

@order.route('/order/<int:order_id>', methods=['GET', 'POST'])
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    form = OrderEditForm(obj=order)
    if form.validate_on_submit():
        order.status = form.status.data
        order.comment = form.comment.data
        db.session.commit()
        flash('Bestellstatus und Kommentar aktualisiert!')
        return redirect(url_for('order.order_detail', order_id=order.id))
    return render_template('order/detail.html', order=order, form=form)

@order.route('/order/history')
def order_history():
    return render_template('order/history.html')
