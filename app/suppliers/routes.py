from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.suppliers import suppliers
from app.models import Supplier, Asset, asset_suppliers
from app import db
from app.suppliers.supplier_utils import import_suppliers_from_csv
from app.admin import permission_required
from werkzeug.utils import secure_filename
from app.suppliers.forms import SupplierForm
import os
from sqlalchemy import distinct

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

@suppliers.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
def supplier_add():
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
            name=form.name.data,
            address=form.address.data,
            phone=form.phone.data,
            email=form.email.data,
            website=form.website.data,
            contact_name=form.contact_name.data,
            customer_number=form.customer_number.data,
            creditor_number=form.creditor_number.data
        )
        db.session.add(supplier)
        db.session.commit()
        flash(f'Lieferant "{supplier.name}" wurde erfolgreich angelegt', 'success')
        return redirect(url_for('suppliers.supplier_list'))
    return render_template('suppliers/edit.html', form=form, title='Neuen Lieferanten anlegen')

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

@suppliers.route('/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
def supplier_edit(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    form = SupplierForm(obj=supplier)
    
    if form.validate_on_submit():
        form.populate_obj(supplier)
        db.session.commit()
        flash(f'Lieferant "{supplier.name}" wurde erfolgreich aktualisiert', 'success')
        return redirect(url_for('suppliers.supplier_list'))
        
    return render_template('suppliers/edit.html', form=form, supplier=supplier, title='Lieferant bearbeiten')

@suppliers.route('/suppliers/detail/<int:supplier_id>')
@login_required
def supplier_detail(supplier_id):
    """Detailansicht eines Lieferanten mit zugeordneten Assets"""
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Zuerst alle eindeutigen Asset-IDs über die asset_suppliers-Tabelle ermitteln
    asset_ids_subquery = db.session.query(distinct(Asset.id))\
                         .join(asset_suppliers)\
                         .filter(asset_suppliers.c.supplier_id == supplier_id)\
                         .all()
    
    # IDs extrahieren
    asset_ids = [row[0] for row in asset_ids_subquery]
    
    # Assets laden und nach Namen sortieren
    assets = []
    if asset_ids:
        assets = Asset.query.filter(Asset.id.in_(asset_ids)).order_by(Asset.name).all()
        
    return render_template(
        'suppliers/detail.html', 
        supplier=supplier, 
        assets=assets,
        asset_count=len(assets)
    )

@suppliers.route('/suppliers/assign_assets/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
def supplier_assign_assets(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    
    if request.method == 'POST':
        # Aktuelle Asset-Zuordnungen entfernen
        supplier.assets = []
        
        # Neue Zuordnungen hinzufügen
        selected_asset_ids = request.form.getlist('asset_ids')
        if selected_asset_ids:
            assets = Asset.query.filter(Asset.id.in_(selected_asset_ids)).all()
            for asset in assets:
                supplier.assets.append(asset)
        
        # Änderungen speichern
        db.session.commit()
        
        # Erfolgsmeldung anzeigen
        flash(f'{len(selected_asset_ids)} Assets wurden dem Lieferanten {supplier.name} zugeordnet.', 'success')
        
        # Zurück zur Detailansicht
        return redirect(url_for('suppliers.supplier_detail', supplier_id=supplier.id))
    
    # Alle verfügbaren Assets laden
    assets = Asset.query.order_by(Asset.name).all()
    
    # IDs der bereits zugeordneten Assets ermitteln
    assigned_asset_ids = [asset.id for asset in supplier.assets]
    
    # Template rendern
    return render_template('suppliers/assign_assets.html', supplier=supplier, assets=assets, assigned_asset_ids=assigned_asset_ids)

@suppliers.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
@login_required
def supplier_delete(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    supplier_name = supplier.name
    
    # Prüfen, ob der Lieferant mit Bestellungen verknüpft ist
    from app.models import Order
    orders_count = Order.query.filter_by(supplier_id=supplier_id).count()
    
    if orders_count > 0:
        flash(f'Der Lieferant "{supplier_name}" kann nicht gelöscht werden, da er mit {orders_count} Bestellung(en) verknüpft ist.', 'danger')
        return redirect(url_for('suppliers.supplier_list'))
    
    try:
        # Verknüpfungen zu Assets entfernen
        from app.models import asset_suppliers
        db.session.execute(asset_suppliers.delete().where(asset_suppliers.c.supplier_id == supplier_id))
        
        # Lieferant löschen
        db.session.delete(supplier)
        db.session.commit()
        flash(f'Lieferant "{supplier_name}" wurde erfolgreich gelöscht', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen des Lieferanten: {str(e)}', 'danger')
    
    return redirect(url_for('suppliers.supplier_list'))
