from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app
from .models import Asset, db, Loan, Document, CostEntry, InventorySession, InventoryItem, InventoryTeam
from .forms import AssetForm, LoanForm, DocumentForm, CostEntryForm, InventorySessionForm, InventoryTeamForm, InventoryCheckForm
import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta
import qrcode
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
import io
from sqlalchemy import func, or_
from dateutil.relativedelta import relativedelta
from flask_login import login_required, current_user
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from flask import send_file
import tempfile
import os

from app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)


main = Blueprint('main', __name__)

@main.route('/locations')
def locations():
    from .models import Location
    locations = Location.query.order_by(Location.name).all()
    return render_template('locations.html', locations=locations)

@main.route('/locations/add', methods=['GET', 'POST'])
def add_location():
    from .models import Location, db
    from .forms import LocationForm
    form = LocationForm()
    if form.validate_on_submit():
        location = Location(
            name=form.name.data,
            street=form.street.data,
            postal_code=form.postal_code.data,
            city=form.city.data,
            state=form.state.data,
            size_sqm=form.size_sqm.data,
            seats=form.seats.data,
            description=form.description.data,
            image_url=form.image_url.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data
        )
        db.session.add(location)
        db.session.commit()
        flash('Standort erfolgreich angelegt.', 'success')
        return redirect(url_for('main.locations'))
    return render_template('location_form.html', form=form)

@main.route('/locations/<int:id>')
def location_detail(id):
    from .models import Location
    location = Location.query.get_or_404(id)
    return render_template('location_detail.html', location=location)

@main.route('/locations/<int:id>/edit', methods=['GET', 'POST'])
def edit_location(id):
    from .models import Location, db
    from .forms import LocationForm
    location = Location.query.get_or_404(id)
    form = LocationForm(obj=location)
    if form.validate_on_submit():
        form.populate_obj(location)
        db.session.commit()
        flash('Standort erfolgreich aktualisiert.', 'success')
        return redirect(url_for('main.location_detail', id=location.id))
    return render_template('location_form.html', form=form, edit=True, location=location)

@main.route('/locations/<int:id>/delete', methods=['POST', 'GET'])
def delete_location(id):
    from .models import Location, db
    location = Location.query.get_or_404(id)
    if request.method == 'POST':
        db.session.delete(location)
        db.session.commit()
        flash('Standort gelöscht.', 'success')
        return redirect(url_for('main.locations'))
    return render_template('confirm_delete.html', object=location, type='Standort', back_url=url_for('main.location_detail', id=id))

@main.route('/assignments/add', methods=['POST'])
def add_assignment():
    from .models import Assignment, db
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    if not name:
        return jsonify({'status': 'error', 'message': 'Name ist erforderlich.'}), 400
    # Prüfe auf Duplikate
    if Assignment.query.filter_by(name=name).first():
        return jsonify({'status': 'error', 'message': 'Name existiert bereits.'}), 400
    assignment = Assignment(name=name, description=description)
    db.session.add(assignment)
    db.session.commit()
    return jsonify({'status': 'success', 'id': assignment.id, 'name': assignment.name})

@main.route('/manufacturers/add', methods=['POST'])
def add_manufacturer():
    from .models import Manufacturer, db
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    website = data.get('website')
    contact_info = data.get('contact_info')
    if not name:
        return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
    if Manufacturer.query.filter_by(name=name).first():
        return jsonify({'success': False, 'message': 'Name existiert bereits.'}), 400
    manufacturer = Manufacturer(
        name=name,
        description=description,
        website=website,
        contact_info=contact_info
    )
    db.session.add(manufacturer)
    db.session.commit()
    return jsonify({'success': True, 'id': manufacturer.id, 'name': manufacturer.name})

# Konfiguration für Datei-Uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/')
def index():
    """Dashboard-Ansicht"""
    # Hole die Assets des Benutzers
    user_assets = Asset.query.all()
    
    # Status-Zähler
    active_count = len([a for a in user_assets if a.status == 'active'])
    on_loan_count = len([a for a in user_assets if a.status == 'on_loan'])
    inactive_count = len([a for a in user_assets if a.status == 'inactive'])
    
    # Wertentwicklung über die letzten 6 Monate
    today = datetime.utcnow()
    months = []
    values = []
    
    # Für jeden Monat die Wertentwicklung berechnen
    for i in range(5, -1, -1):
        date = today.replace(day=1) - relativedelta(months=i)
        next_date = date + relativedelta(months=1)
        months.append(date.strftime('%B %Y'))
        
        # Assets finden, die bis zu diesem Monat erstellt wurden
        month_assets = Asset.query.filter(
            Asset.created_at < next_date
        ).all()
        
        # Gesamtwert für diesen Monat berechnen
        total_value = 0
        for asset in month_assets:
            try:
                if asset.value is not None:
                    total_value += float(asset.value)
            except (ValueError, TypeError):
                print(f"Warnung: Ungültiger Wert für Asset {asset.name}: {asset.value}")
                continue
        
        values.append(total_value)
        print(f"\nMonat {date.strftime('%B %Y')}:")
        print(f"Gefundene Assets: {len(month_assets)}")
        print(f"Gesamtwert: {total_value}")
        for asset in month_assets:
            print(f"- {asset.name}: {asset.value} (Erstellt: {asset.created_at})")
    
    # Kategorien
    category_data = []
    categories = {}
    for asset in user_assets:
        cat = asset.category.name if asset.category else 'Ohne Kategorie'
        categories[cat] = categories.get(cat, 0) + 1
    
    for category, count in categories.items():
        category_data.append({
            'category': category,
            'count': count
        })
    
    # Kostenverteilung
    cost_types = {
        'purchase': 'Anschaffung',
        'maintenance': 'Wartung',
        'repair': 'Reparatur',
        'upgrade': 'Upgrade/Erweiterung',
        'insurance': 'Versicherung',
        'other': 'Sonstiges'
    }
    
    costs = {'Anschaffung': 0}  # Initialisiere mit Anschaffungskosten
    # Alle Assets für die Kostenberechnung verwenden
    all_assets = Asset.query.all()
    
    # Erst die Anschaffungskosten (value) der Assets summieren
    for asset in all_assets:
        if asset.value:
            costs['Anschaffung'] += float(asset.value)
    
    # Dann die zusätzlichen Kosteneinträge hinzufügen
    for asset in all_assets:
        if hasattr(asset, 'cost_entries'):
            for entry in asset.cost_entries:
                cost_type = cost_types.get(entry.cost_type, 'Sonstiges')
                if cost_type != 'Anschaffung':  # Vermeide Doppelzählung von Anschaffungskosten
                    costs[cost_type] = costs.get(cost_type, 0) + entry.amount
    
    # Entferne Kostentypen mit 0 Kosten
    costs = {k: v for k, v in costs.items() if v > 0}
    
    cost_type_labels = list(costs.keys())
    cost_amounts = [costs[label] for label in cost_type_labels]
    
    print("\nKostenverteilung:")
    for label, amount in zip(cost_type_labels, cost_amounts):
        print(f"{label}: {amount}")
    
    # Letzte Assets
    recent_assets = Asset.query.order_by(Asset.created_at.desc()).limit(5).all()
    
    # Standorte für die Karte (wie im dashboard-View)
    from .models import Location
    location_objs = Location.query.filter(Location.latitude.isnot(None), Location.longitude.isnot(None)).all()
    locations = [
        {
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'street': loc.street,
            'postal_code': loc.postal_code,
            'city': loc.city,
            'description': loc.description
        }
        for loc in location_objs
    ]

    return render_template('dashboard.html',
        active_count=active_count,
        on_loan_count=on_loan_count,
        inactive_count=inactive_count,
        months=months,
        values=values,
        category_data=category_data,
        cost_type_labels=cost_type_labels,
        cost_amounts=cost_amounts,
        recent_assets=recent_assets,
        locations=locations
    )

@main.route('/dashboard')
def dashboard():
    # Hole die letzten 5 Assets des Benutzers
    recent_assets = Asset.query.order_by(Asset.id.desc()).limit(5).all()
    
    # Statistiken für die Charts
    total_assets = Asset.query.count()
    on_loan = Asset.query.filter_by(status='on_loan').count()
    inactive = Asset.query.filter_by(status='inactive').count()
    active = total_assets - on_loan - inactive

    # Debug: Zeige alle Assets und ihre Werte
    print("\nAlle Assets und ihre Werte:")
    all_assets = Asset.query.all()
    for asset in all_assets:
        print(f"Asset: {asset.name}, Wert: {asset.value}, Erstellt am: {asset.created_at}")

    # Wertentwicklung über die letzten 6 Monate
    today = datetime.utcnow()
    months = []
    values = []
    
    print("\nWertentwicklung Berechnung:")
    # Für jeden Monat die Wertentwicklung berechnen
    for i in range(5, -1, -1):
        date = today.replace(day=1) - relativedelta(months=i)
        next_date = date + relativedelta(months=1)
        months.append(date.strftime('%B %Y'))
        
        # Assets finden, die bis zu diesem Monat erstellt wurden
        month_assets = Asset.query.filter(
            Asset.created_at < next_date
        ).all()
        
        # Gesamtwert für diesen Monat berechnen
        total_value = 0
        for asset in month_assets:
            try:
                if asset.value is not None:
                    total_value += float(asset.value)
            except (ValueError, TypeError):
                print(f"Warnung: Ungültiger Wert für Asset {asset.name}: {asset.value}")
                continue
        
        values.append(total_value)
        print(f"\nMonat {date.strftime('%B %Y')}:")
        print(f"Gefundene Assets: {len(month_assets)}")
        print(f"Gesamtwert: {total_value}")
        for asset in month_assets:
            print(f"- {asset.name}: {asset.value} (Erstellt: {asset.created_at})")
        
        print("\nBerechnete Werte:")
        print("Monate:", months)
        print("Werte:", values)

    # Kategorien
    category_data = []
    categories = {}
    for asset in recent_assets:
        cat = asset.category or 'Ohne Kategorie'
        categories[cat] = categories.get(cat, 0) + 1
    
    for category, count in categories.items():
        category_data.append({
            'category': category,
            'count': count
        })
    
    # Kostenverteilung
    cost_types = {
        'purchase': 'Anschaffung',
        'maintenance': 'Wartung',
        'repair': 'Reparatur',
        'upgrade': 'Upgrade/Erweiterung',
        'insurance': 'Versicherung',
        'other': 'Sonstiges'
    }
    
    costs = {'Anschaffung': 0}  # Initialisiere mit Anschaffungskosten
    # Alle Assets für die Kostenberechnung verwenden
    all_assets = Asset.query.all()
    
    # Erst die Anschaffungskosten (value) der Assets summieren
    for asset in all_assets:
        if asset.value:
            costs['Anschaffung'] += float(asset.value)
    
    # Dann die zusätzlichen Kosteneinträge hinzufügen
    for asset in all_assets:
        if hasattr(asset, 'cost_entries'):
            for entry in asset.cost_entries:
                cost_type = cost_types.get(entry.cost_type, 'Sonstiges')
                if cost_type != 'Anschaffung':  # Vermeide Doppelzählung von Anschaffungskosten
                    costs[cost_type] = costs.get(cost_type, 0) + entry.amount
    
    # Entferne Kostentypen mit 0 Kosten
    costs = {k: v for k, v in costs.items() if v > 0}
    
    cost_type_labels = list(costs.keys())
    cost_amounts = list(costs.values())

    # Kategorien-Statistiken (nur Klartextnamen)
    from .models import Category
    # Zeige alle Kategorien (auch neue/ohne Assets) im Chart, aber zähle nur aktive Assets
    categories = db.session.query(
        Category.name,
        func.count(Asset.id)
    ).outerjoin(Asset, (Asset.category_id == Category.id) & (Asset.status == 'active'))\
     .group_by(Category.id, Category.name)\
     .order_by(Category.name)\
     .all()
    category_data = [{
        'category': cat_name or 'Ohne Kategorie',
        'count': count
    } for cat_name, count in categories]
    # Assets ohne Kategorie ergänzen (nur aktive)
    no_category_count = Asset.query.filter((Asset.category == None) & (Asset.status == 'active')).count()
    if no_category_count:
        category_data.append({'category': 'Ohne Kategorie', 'count': no_category_count})

    # Debug-Ausgabe
    print('Kategorie-Auswertung für Dashboard (nur aktive Assets):')
    for entry in category_data:
        print(entry)

    # Standorte für die Karte (nur mit Koordinaten)
    from .models import Location
    location_objs = Location.query.filter(Location.latitude.isnot(None), Location.longitude.isnot(None)).all()
    locations = [
        {
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'street': loc.street,
            'postal_code': loc.postal_code,
            'city': loc.city,
            'description': loc.description
        }
        for loc in location_objs
    ]
    return render_template('dashboard.html',
        recent_assets=recent_assets,
        active_count=active,
        on_loan_count=on_loan,
        inactive_count=inactive,
        months=months,
        values=values,
        category_data=category_data,
        cost_type_labels=cost_type_labels,
        cost_amounts=cost_amounts,
        locations=locations
    )

@main.route('/assets')
def assets():
    """Asset-Übersicht mit Filterfunktion"""
    from .models import Assignment, Manufacturer, Supplier
    query = Asset.query

    # Filter: Name (Textfeld)
    name = request.args.get('name', '').strip()
    if name:
        query = query.filter(Asset.name.ilike(f"%{name}%"))

    # Filter: Kategorie (Dropdown)
    category = request.args.get('category', '')
    if category:
        query = query.filter(Asset.category_id == int(category))

    # Filter: Standort (Dropdown)
    location = request.args.get('location', '')
    if location:
        query = query.filter(Asset.location == location)

    # Filter: Hersteller (Dropdown)
    manufacturer_id = request.args.get('manufacturer', '')
    if manufacturer_id:
        query = query.filter(Asset.manufacturers.any(Manufacturer.id == int(manufacturer_id)))

    # Filter: Lieferant (Dropdown)
    supplier_id = request.args.get('supplier', '')
    if supplier_id:
        query = query.filter(Asset.suppliers.any(Supplier.id == int(supplier_id)))

    # Filter: Zuordnung (Dropdown)
    assignment_id = request.args.get('assignment', '')
    if assignment_id:
        query = query.filter(Asset.assignments.any(Assignment.id == int(assignment_id)))

    # Filter: Nur mit Bild (Checkbox)
    with_image = request.args.get('with_image', '')
    if with_image:
        query = query.filter(Asset.image_url != None)

    assets = query.all()

    # AssetForm instanziieren, um auf die Choices zuzugreifen
    form = AssetForm()
    categories = [(c[0], c[1]) for c in form.category.choices if c[0]]
    locations = [(l[0], l[1]) for l in form.location_id.choices if l[0]]
    manufacturers = [(str(m.id), m.name) for m in Manufacturer.query.order_by(Manufacturer.name).all()]
    suppliers = [(str(s.id), s.name) for s in Supplier.query.order_by(Supplier.name).all()]
    assignments = [(str(a.id), a.name) for a in Assignment.query.order_by(Assignment.name).all()]

    return render_template(
        'assets.html',
        assets=assets,
        categories=categories,
        locations=locations,
        manufacturers=manufacturers,
        suppliers=suppliers,
        assignments=assignments,
        selected={
            'name': name,
            'category': category,
            'location': location,
            'manufacturer': manufacturer_id,
            'supplier': supplier_id,
            'assignment': assignment_id,
            'with_image': with_image
        }
    )

@main.route('/categories/add', methods=['POST'])
def add_category():
    from .models import Category
    from . import db
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({'success': False, 'message': 'Kategorie existiert bereits'}), 400
    category = Category(name=data['name'])
    db.session.add(category)
    try:
        db.session.commit()
        return jsonify({'success': True, 'id': category.id, 'name': category.name})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@main.route('/categories/delete', methods=['POST'])
def delete_category():
    from .models import Category
    from . import db
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
    category = Category.query.filter_by(name=data['name']).first()
    if not category:
        return jsonify({'success': False, 'message': 'Kategorie nicht gefunden'}), 404
    db.session.delete(category)
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@main.route('/add_asset', methods=['GET', 'POST'])
def add_asset():
    from .models import Assignment, Manufacturer, Supplier
    form = AssetForm()
    doc_form = DocumentForm()
    
    if form.validate_on_submit():
        asset = Asset(
            name=form.name.data,
            category_id=int(form.category.data) if form.category.data else None,
            value=form.value.data,
            status=form.status.data,
            location_id=form.location_id.data if form.location_id.data else None,
            article_number=form.article_number.data,
            ean=form.ean.data,
            serial_number=form.serial_number.data,
            purchase_date=form.purchase_date.data
        )
        # IDs als Liste holen (Strings zu int)
        assignment_ids = [int(i) for i in request.form.getlist('assignments')]
        manufacturer_ids = [int(i) for i in request.form.getlist('manufacturers')]
        supplier_ids = [int(i) for i in request.form.getlist('suppliers')]
        # Relationen setzen
        asset.assignments = Assignment.query.filter(Assignment.id.in_(assignment_ids)).all() if assignment_ids else []
        asset.manufacturers = Manufacturer.query.filter(Manufacturer.id.in_(manufacturer_ids)).all() if manufacturer_ids else []
        asset.suppliers = Supplier.query.filter(Supplier.id.in_(supplier_ids)).all() if supplier_ids else []
        # Bild-Upload verarbeiten
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            # Eindeutigen Dateinamen erzeugen
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            img_folder = os.path.join(current_app.static_folder, 'images')
            if not os.path.exists(img_folder):
                os.makedirs(img_folder)
            form.image.data.save(os.path.join(img_folder, filename))
            asset.image_url = f"/static/images/{filename}"
        db.session.add(asset)
        db.session.commit()
        
        flash('Asset wurde erfolgreich erstellt.', 'success')
        return redirect(url_for('main.edit_asset', id=asset.id))
    
    return render_template('edit_asset.html', form=form, doc_form=doc_form, asset=None, documents=[], is_new=True)

@main.route('/edit_asset/<int:id>', methods=['GET', 'POST'])
def edit_asset(id):
    from .models import Assignment, Manufacturer, Supplier
    asset = Asset.query.get_or_404(id)
    form = AssetForm(obj=asset)
    doc_form = DocumentForm()
    # Multi-Select-Felder mit aktuellen IDs befüllen
    form.assignments.data = [str(a.id) for a in asset.assignments]
    form.manufacturers.data = [str(m.id) for m in asset.manufacturers]
    form.suppliers.data = [str(s.id) for s in asset.suppliers]
    
    if form.validate_on_submit():
        asset.name = form.name.data
        from .models import Category
        asset.category_id = int(form.category.data) if form.category.data else None
        asset.value = form.value.data
        asset.status = form.status.data
        asset.location_id = int(form.location_id.data) if form.location_id.data else None
        asset.article_number = form.article_number.data
        asset.ean = form.ean.data
        asset.serial_number = form.serial_number.data
        asset.purchase_date = form.purchase_date.data
        # IDs als Liste holen (Strings zu int)
        assignment_ids = request.form.getlist('assignments')
        manufacturer_ids = request.form.getlist('manufacturers')
        supplier_ids = request.form.getlist('suppliers')
        # Relationen setzen (nur wenn IDs übergeben wurden, sonst unverändert lassen)
        if assignment_ids:
            asset.assignments = Assignment.query.filter(Assignment.id.in_(assignment_ids)).all()
        if manufacturer_ids:
            asset.manufacturers = Manufacturer.query.filter(Manufacturer.id.in_(manufacturer_ids)).all()
        if supplier_ids:
            asset.suppliers = Supplier.query.filter(Supplier.id.in_(supplier_ids)).all()
        # Bild-Upload beim Bearbeiten
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            img_folder = os.path.join(current_app.static_folder, 'images')
            if not os.path.exists(img_folder):
                os.makedirs(img_folder)
            form.image.data.save(os.path.join(img_folder, filename))
            asset.image_url = f"/static/images/{filename}"
        db.session.commit()
        flash('Asset wurde erfolgreich aktualisiert.', 'success')
        return redirect(url_for('main.assets'))
    
    documents = Document.query.filter_by(asset_id=id).all()
    return render_template('edit_asset.html', form=form, doc_form=doc_form, asset=asset, documents=documents, is_new=False)

@main.route('/loan_asset/<int:id>', methods=['GET', 'POST'])
def loan_asset(id):
    """Asset ausleihen"""
    asset = Asset.query.get_or_404(id)
    
    if asset.on_loan:
        flash('Dieses Asset ist bereits ausgeliehen.', 'error')
        return redirect(url_for('main.assets'))
    
    form = LoanForm()
    if form.validate_on_submit():
        loan = Loan(
            asset_id=asset.id,
            borrower_name=form.borrower_name.data,
            start_date=form.start_date.data,
            expected_return_date=form.expected_return_date.data,
            notes=form.notes.data
        )
        asset.status = 'on_loan'
        db.session.add(loan)
        db.session.commit()
        flash('Asset wurde erfolgreich ausgeliehen.', 'success')
        return redirect(url_for('main.assets'))
    
    return render_template('loan_asset.html', form=form, asset=asset)

@main.route('/return_asset/<int:id>', methods=['POST'])
def return_asset(id):
    """Asset zurückgeben"""
    asset = Asset.query.get_or_404(id)
    
    if not asset.on_loan:
        flash('Dieses Asset ist nicht ausgeliehen.', 'error')
        return redirect(url_for('main.assets'))
    
    # Finde das aktuelle Ausleih-Objekt
    loan = Loan.query.filter_by(asset_id=id, return_date=None).first()
    if loan:
        loan.return_date = datetime.utcnow()
        asset.status = 'active'
        db.session.commit()
        flash('Asset wurde erfolgreich zurückgegeben.', 'success')
    
    return redirect(url_for('main.assets'))

@main.route('/upload_document/<int:id>', methods=['POST'])
def upload_document(id):
    asset = Asset.query.get_or_404(id)
    
    form = DocumentForm()
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        
        document = Document(
            title=form.title.data,
            document_type=form.document_type.data,
            filename=filename,
            notes=form.notes.data,
            asset_id=id,
            size=len(file.read())
        )
        
        file.seek(0)  # Zurück zum Anfang der Datei
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        
        db.session.add(document)
        db.session.commit()
        
        flash('Dokument wurde erfolgreich hochgeladen.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return redirect(url_for('main.edit_asset', id=id))

@main.route('/download_document/<int:document_id>')
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    return send_from_directory(
        UPLOAD_FOLDER,
        document.filename,
        as_attachment=True,
        download_name=f"{document.title}{os.path.splitext(document.filename)[1]}"
    )

@main.route('/preview_document/<int:document_id>')
def preview_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    return send_from_directory(
        UPLOAD_FOLDER,
        document.filename,
        as_attachment=False
    )

@main.route('/delete_document/<int:document_id>', methods=['POST'])
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    asset_id = document.asset_id
    
    # Lösche die Datei
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, document.filename))
    except OSError:
        pass  # Ignoriere Fehler beim Löschen der Datei
    
    # Lösche den Datenbankeintrag
    db.session.delete(document)
    db.session.commit()
    
    flash('Dokument wurde erfolgreich gelöscht.', 'success')
    return redirect(url_for('main.edit_asset', id=asset_id))

@main.route('/assets/<int:id>/delete', methods=['POST'])
def delete_asset(id):
    """Asset und alle verknüpften Daten löschen"""
    asset = Asset.query.filter_by(id=id).first_or_404()
    
    # Lösche alle verknüpften Dokumente
    documents = Document.query.filter_by(asset_id=id).all()
    for doc in documents:
        if doc.filename:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, doc.filename))
            except OSError:
                pass  # Ignoriere Fehler beim Löschen der Datei
        db.session.delete(doc)
    
    # Lösche alle Kosteneinträge und deren Belege
    cost_entries = CostEntry.query.filter_by(asset_id=id).all()
    for entry in cost_entries:
        if entry.receipt_file:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, entry.receipt_file))
            except OSError:
                pass
        db.session.delete(entry)
    
    # Lösche alle Ausleihvorgänge
    loans = Loan.query.filter_by(asset_id=id).all()
    for loan in loans:
        db.session.delete(loan)
    
    # Lösche das Asset selbst
    db.session.delete(asset)
    db.session.commit()
    
    flash('Asset und alle verknüpften Daten wurden erfolgreich gelöscht.', 'success')
    return jsonify({'success': True})

@main.route('/import_assets', methods=['GET', 'POST'])
def import_assets():
    """CSV Import für Assets"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Keine Datei ausgewählt.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Keine Datei ausgewählt.', 'error')
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash('Bitte wählen Sie eine CSV-Datei aus.', 'error')
            return redirect(request.url)
        
        try:
            # Lese die CSV-Datei
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            # Importiere die Assets
            for row in csv_input:
                asset = Asset(
                    name=row['name'],
                    category=row['category'],
                    value=float(row['value']),
                    status='active'
                )
                db.session.add(asset)
            
            db.session.commit()
            flash('Assets wurden erfolgreich importiert.', 'success')
            return redirect(url_for('main.assets'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Import: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('import_assets.html')

@main.route('/assets/<int:id>/qr')
def asset_qr(id):
    asset = Asset.query.filter_by(id=id).first_or_404()
    
    # QR-Code mit Asset-Informationen generieren
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Asset-URL und grundlegende Informationen im QR-Code
    data = {
        'id': asset.id,
        'name': asset.name,
        'category': asset.category,
        'location': asset.location
    }
    qr.add_data(str(data))
    qr.make(fit=True)

    # QR-Code als Bild erzeugen
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Bild in BytesIO-Objekt speichern
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@main.route('/assets/<int:id>/documents', methods=['GET', 'POST'])
def asset_documents(id):
    asset = Asset.query.get_or_404(id)
    
    form = DocumentForm()
    if form.validate_on_submit():
        file = form.file.data
        if file and allowed_file(file.filename):
            # Sichere Dateinamen generieren
            filename = secure_filename(f"receipt_{file.filename}")
            
            # Speichere die Datei
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            # Dokument in der Datenbank speichern
            document = Document(
                asset_id=asset.id,
                title=form.title.data,
                document_type=form.document_type.data,
                filename=filename,
                file_path=file_path,
                mime_type=file.content_type,
                size=os.path.getsize(file_path),
                notes=form.notes.data
            )
            
            db.session.add(document)
            db.session.commit()
            
            flash('Dokument wurde erfolgreich hochgeladen.', 'success')
            return redirect(url_for('main.asset_documents', id=asset.id))
        else:
            flash('Ungültiger Dateityp.', 'error')
    
    documents = Document.query.filter_by(asset_id=asset.id).order_by(Document.upload_date.desc()).all()
    return render_template('documents.html', form=form, asset=asset, documents=documents)

@main.route('/assets/<int:id>/costs')
def asset_costs(id):
    """Zeigt die Kosten eines Assets an"""
    asset = Asset.query.get_or_404(id)
    
    form = CostEntryForm()
    cost_entries = CostEntry.query.filter_by(asset_id=id).order_by(CostEntry.date.desc()).all()
    
    return render_template(
        'cost_entries.html',
        asset=asset,
        form=form,
        cost_entries=cost_entries
    )

@main.route('/assets/<int:id>/costs/add', methods=['POST'])
def add_cost_entry(id):
    """Fügt einen neuen Kosteneintrag hinzu"""
    asset = Asset.query.get_or_404(id)
    
    form = CostEntryForm()
    if form.validate_on_submit():
        receipt_file = form.receipt.data
        filename = None
        if receipt_file:
            filename = secure_filename(receipt_file.filename)
            receipt_file.save(os.path.join(UPLOAD_FOLDER, filename))
        
        cost_entry = CostEntry(
            asset_id=id,
            cost_type=form.cost_type.data,
            amount=form.amount.data,
            date=form.date.data,
            description=form.description.data,
            receipt_file=filename
        )
        db.session.add(cost_entry)
        db.session.commit()
        flash('Kosteneintrag wurde erfolgreich hinzugefügt.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return redirect(url_for('main.asset_costs', id=id))

@main.route('/costs/<int:id>/delete', methods=['POST'])
def delete_cost_entry(id):
    """Löscht einen Kosteneintrag"""
    cost_entry = CostEntry.query.get_or_404(id)
    
    asset_id = cost_entry.asset_id
    
    # Lösche die Belegdatei, falls vorhanden
    if cost_entry.receipt_file:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, cost_entry.receipt_file))
        except OSError:
            pass
    
    db.session.delete(cost_entry)
    db.session.commit()
    flash('Kosteneintrag wurde erfolgreich gelöscht.', 'success')
    return redirect(url_for('main.asset_costs', id=asset_id))

@main.route('/costs/<int:id>/receipt')
def download_receipt(id):
    """Lädt den Beleg eines Kosteneintrags herunter"""
    cost_entry = CostEntry.query.get_or_404(id)
    
    if not cost_entry.receipt_file:
        abort(404)
    
    return send_from_directory(
        UPLOAD_FOLDER,
        cost_entry.receipt_file,
        as_attachment=True,
        download_name=f"Beleg_{cost_entry.date.strftime('%Y%m%d')}_{cost_entry.cost_type}{os.path.splitext(cost_entry.receipt_file)[1]}"
    )

@main.route('/assets/<int:id>')
def asset_details(id):
    asset = Asset.query.get_or_404(id)
    
    documents = Document.query.filter_by(asset_id=id).all()
    return render_template('asset_details.html', asset=asset, documents=documents)

@main.route('/inventory/planning', methods=['GET'])
def inventory_planning():
    """Zeigt die Inventurplanung an"""
    # Hole aktive und geplante Inventuren
    active_sessions = InventorySession.query.filter(
        InventorySession.status.in_(['planned', 'active'])
    ).order_by(InventorySession.start_date).all()
    
    # Hole abgeschlossene Inventuren (die letzten 5)
    completed_sessions = InventorySession.query.filter_by(
        status='completed'
    ).order_by(InventorySession.end_date.desc()).limit(5).all()
    
    return render_template('inventory/planning.html',
        active_sessions=active_sessions,
        completed_sessions=completed_sessions
    )

@main.route('/inventory/planning/new', methods=['GET', 'POST'])
def inventory_planning_new():
    """Neue Inventur planen"""
    form = InventorySessionForm()
    
    if form.validate_on_submit():
        # Konvertiere die Datumswerte zu DateTime mit Standardzeit
        start_date = datetime.combine(form.start_date.data, datetime.min.time())
        end_date = datetime.combine(form.end_date.data, datetime.max.time())
        
        session = InventorySession(
            name=form.name.data,
            start_date=start_date,
            end_date=end_date,
            location_id=form.location_id.data if form.location_id.data != 0 else None,
            notes=form.notes.data,
            status='planned'
        )
        db.session.add(session)
        db.session.commit()
        
        # Automatisch alle Assets am gewählten Standort zur Inventur hinzufügen
        assets = Asset.query.filter_by(location_id=form.location_id.data if form.location_id.data != 0 else None).all()
        for asset in assets:
            item = InventoryItem(
                session_id=session.id,
                asset_id=asset.id,
                expected_quantity=1,  # Hier explizit Soll-Menge setzen
                expected_location=session.location_obj.name if session.location_obj else asset.location
            )
            print("CREATE InventoryItem:", asset.name, "expected_quantity:", item.expected_quantity)
            db.session.add(item)
        
        db.session.commit()
        flash('Inventur wurde erfolgreich geplant.', 'success')
        return redirect(url_for('main.inventory_planning_detail', id=session.id))
    
    return render_template('inventory/planning_new.html', form=form)

@main.route('/inventory/planning/<int:id>', methods=['GET', 'POST'])

def inventory_planning_detail(id):
    """Details einer geplanten Inventur"""
    session = InventorySession.query.get_or_404(id)
    
    if request.method == 'POST':
        # Inline-Erfassung: Mengen und Felder für alle Gruppen übernehmen
        group_count = int(request.form.get('group_count', 0))
        updated_any = False
        for i in range(group_count):
            group_name = request.form.get(f'group_name_{i}')
            group_article_number = request.form.get(f'group_article_number_{i}')
            counted_quantity = int(request.form.get(f'counted_quantity_{i}', 0))
            damaged_quantity = int(request.form.get(f'damaged_quantity_{i}', 0))
            actual_location = request.form.get(f'actual_location_{i}', '')
            notes = request.form.get(f'notes_{i}', '')

            # Gruppensuche maximal tolerant
            def norm(val):
                return (val or '').strip().lower()
            def is_no_artnr(val):
                return val is None or str(val).strip() == '' or str(val).strip() == '-'
            all_items = InventoryItem.query.filter_by(session_id=session.id).all()
            key_name = norm(group_name)
            key_artnr = norm(group_article_number)
            if is_no_artnr(group_article_number):
                items_same_type = [it for it in all_items if norm(it.asset.name) == key_name and is_no_artnr(it.asset.article_number)]
            else:
                items_same_type = [it for it in all_items if norm(it.asset.name) == key_name and norm(it.asset.article_number) == key_artnr]
            # Mengen und Felder übernehmen
            for idx, it in enumerate(items_same_type):
                if idx < counted_quantity:
                    if idx < damaged_quantity:
                        it.status = 'damaged'
                        it.condition = 'damaged'
                    else:
                        it.status = 'found'
                        it.condition = 'good'
                    it.counted_quantity = 1
                else:
                    it.status = 'missing'
                    it.condition = 'missing'
                    it.counted_quantity = 0
                it.actual_location = actual_location
                it.notes = notes
                updated_any = True
        if updated_any:
            db.session.commit()
            # Wenn Inventur abschließen ausgelöst wurde, leite weiter zur Abschlussroute
            if request.form.get('complete_inventory') == '1':
                # Abschluss-Logik direkt als Funktionsaufruf (POST bleibt erhalten)
                return complete_inventory(session.id)
            else:
                flash('Alle Mengen und Felder wurden gespeichert.', 'success')
                return redirect(url_for('main.inventory_planning_detail', id=session.id))

        # Ursprüngliche Standortauswahl-Logik (Assets hinzufügen)
        location = request.form.get('location')
        if location:
            # Alle Assets am ausgewählten Standort zur Inventur hinzufügen
            assets = Asset.query.filter_by(location=location).all()
            for asset in assets:
                # Prüfen ob das Asset bereits in der Inventur ist
                if not InventoryItem.query.filter_by(session_id=id, asset_id=asset.id).first():
                    item = InventoryItem(
                        session_id=id,
                        asset_id=asset.id,
                        expected_quantity=1,
                        expected_location=asset.location,
                        status='pending'
                    )
                    db.session.add(item)
            
            db.session.commit()
            flash(f'Assets vom Standort {location} wurden hinzugefügt.', 'success')
            
    # Alle verfügbaren Standorte für das Dropdown
    locations = db.session.query(Asset.location).distinct().all()
    locations = [loc[0] for loc in locations if loc[0]]  # Leere Standorte ausfiltern
    
    # Aktuelle Items der Inventur
    items = (InventoryItem.query
            .join(Asset)
            .filter(InventoryItem.session_id == id)
            .all())

    # Gruppierung nach Asset-Name und Artikelnummer (maximal tolerant)
    from collections import defaultdict
    def norm(val):
        return (val or '').strip().lower()
    def is_no_artnr(val):
        return val is None or str(val).strip() == '' or str(val).strip() == '-'
    items_grouped = defaultdict(lambda: {"name": None, "article_number": None, "category": None, "expected_location": None, "sum_expected_quantity": 0, "serial_numbers": [], "statuses": set()})
    for item in items:
        name = norm(item.asset.name)
        artnr = item.asset.article_number
        key_artnr = '-' if is_no_artnr(artnr) else norm(artnr)
        key = (name, key_artnr)
        group = items_grouped[key]
        group["name"] = item.asset.name
        group["article_number"] = item.asset.article_number
        group["category"] = item.asset.category.name if item.asset.category else "-"
        group["expected_location"] = item.expected_location or "-"
        group["sum_expected_quantity"] += item.expected_quantity or 1
        # Fix: Gezählte Menge korrekt aufsummieren, nicht überschreiben
        if "sum_counted_quantity" not in group:
            group["sum_counted_quantity"] = 0
        group["sum_counted_quantity"] += item.counted_quantity or 0
        if item.asset.serial_number:
            group["serial_numbers"].append(item.asset.serial_number)
        group["statuses"].add(item.status)
    # sets zu listen für jinja
    for group in items_grouped.values():
        group["statuses"] = list(group["statuses"])
    items_grouped = list(items_grouped.values())

    # Neue Zähllogik: Summe der Soll- und Ist-Mengen
    def safe_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    total = sum(safe_int(item.expected_quantity) for item in items)
    counted = sum(safe_int(item.counted_quantity) for item in items)
    gefunden = counted  # Die gezählte Menge ist die Anzahl der gefundenen Stücke
    # Gruppiert nach Asset-Name: Zähle, wie viele Asset-Typen noch nicht vollständig gezählt sind
    asset_groups = defaultdict(lambda: {"expected": 0, "counted": 0})
    for item in items:
        print("DEBUG item:", item.asset.name, "expected_quantity:", item.expected_quantity, "counted_quantity:", item.counted_quantity)
        key = item.asset.name
        asset_groups[key]["expected"] += safe_int(item.expected_quantity)
        asset_groups[key]["counted"] += safe_int(item.counted_quantity)
    # Debug-Ausgabe für asset_groups
    print("DEBUG asset_groups:", dict(asset_groups))
    # Ausstehende Stückzahl: Summe aller noch nicht gezählten Stücke
    ausstehende_stueckzahl = sum(
        max(int(group["expected"]) - int(group["counted"]), 0)
        for group in asset_groups.values()
        if int(group["expected"]) > 0 and int(group["counted"]) < int(group["expected"])
    )
    # Ausstehend: Anzahl Asset-Typen, bei denen noch nicht alles gezählt wurde
    ausstehende_assets = sum(
        1 for group in asset_groups.values()
        if int(group["expected"]) > 0 and int(group["counted"]) < int(group["expected"])
    )
    # Fehlend: Summe aller fehlenden Stücke
    fehlend = sum(
        max(int(group["expected"]) - int(group["counted"]), 0)
        for group in asset_groups.values()
        if int(group["expected"]) > 0
    )
    missing = fehlend
    damaged = len([item for item in items if item.status == 'damaged'])
    progress = (counted / total * 100) if total > 0 else 0

    # --- DEBUG: Ausgabe aller InventoryItems der Session ---
    print("\n--- DEBUG InventoryItems für Session", id, "---")
    for item in items:
        print(f"ID: {item.id}, Asset-ID: {item.asset_id}, Asset-Name: {getattr(item.asset, 'name', None)}, Soll: {item.expected_quantity}, Ist: {item.counted_quantity}, Status: {item.status}")
    print("--- ENDE DEBUG ---\n")
    return render_template('inventory/planning_detail.html',
                         session=session,
                         items=items,
                         items_grouped=items_grouped,
                         locations=locations,
                         total=total,
                         counted=counted,
                         gefunden=gefunden,
                         ausstehende_stueckzahl=ausstehende_stueckzahl,
                         ausstehende_assets=ausstehende_assets,
                         missing=missing,
                         damaged=damaged,
                         progress=progress)


@main.route('/inventory/start', methods=['POST'])

def inventory_start():
    id = request.form.get('id', type=int)
    if not id:
        flash('Ungültige Anfrage.', 'error')
        return redirect(url_for('main.inventory_planning'))
    
    session = InventorySession.query.get_or_404(id)
    if session.status != 'planned':
        flash('Diese Inventur kann nicht gestartet werden.', 'error')
        return redirect(url_for('main.inventory_planning_detail', id=id))
    
    session.status = 'active'
    db.session.commit()
    
    flash('Inventur wurde gestartet.', 'success')
    return redirect(url_for('main.inventory_planning_detail', id=id))

@main.route('/inventory/planning/<int:id>/cancel', methods=['POST'])
def inventory_planning_cancel(id):
    """Bricht eine geplante Inventur ab"""
    session = InventorySession.query.get_or_404(id)
    
    if session.status not in ['planned', 'active']:
        flash('Diese Inventur kann nicht abgebrochen werden.', 'error')
        return redirect(url_for('main.inventory_planning_detail', id=id))
    
    session.status = 'cancelled'
    db.session.commit()
    flash('Inventur wurde abgebrochen.', 'success')
    return redirect(url_for('main.inventory_planning'))

@main.route('/inventory/execute')

def inventory_execute():
    """Übersicht der aktiven Inventuren zur Durchführung"""
    # Hole alle aktiven Inventuren
    active_sessions = InventorySession.query.filter_by(status='active').all()
    return render_template('inventory/execute.html', active_sessions=active_sessions)

@main.route('/inventory/execute/<int:id>')

def inventory_execute_session(id):
    """Zeigt die Erfassungsansicht einer Inventur"""
    session = InventorySession.query.get_or_404(id)
    
    if session.status != 'active':
        flash('Diese Inventur ist nicht aktiv.', 'warning')
        return redirect(url_for('main.inventory_execute'))
    
    # Alle Items der Inventur mit Asset-Informationen
    items = (InventoryItem.query
            .join(Asset)
            .filter(InventoryItem.session_id == id)
            .order_by(Asset.name)
            .all())
    
    # Neue Zähllogik: Summe der Soll- und Ist-Mengen
    def safe_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    total = sum(safe_int(item.expected_quantity) for item in items)
    counted = sum(safe_int(item.counted_quantity) for item in items)
    gefunden = counted
    ausstehende_stueckzahl = max(total - counted, 0)
    ausstehende_assets = sum(1 for item in items if safe_int(item.counted_quantity) < safe_int(item.expected_quantity))
    progress = (counted / total * 100) if total > 0 else 0

    return render_template('inventory/execute_session.html',
                         session=session,
                         items=items,
                         total=total,
                         counted=counted,
                         gefunden=gefunden,
                         ausstehende_stueckzahl=ausstehende_stueckzahl,
                         ausstehende_assets=ausstehende_assets,
                         progress=progress)


@main.route('/inventory/check_group/<int:session_id>/<group_name>/<article_number>', methods=['GET', 'POST'])
def inventory_check_group(session_id, group_name, article_number):
    session = InventorySession.query.get_or_404(session_id)
    all_items = InventoryItem.query.filter_by(session_id=session.id).all()
    def norm(val):
        return (val or '').strip().lower()
    key_name = norm(group_name)
    key_artnr = norm(article_number)
    # Maximale Toleranz: Alle Varianten von 'keine Artikelnummer' (None, '', '-') als gleich behandeln
    def is_no_artnr(val):
        return val is None or str(val).strip() == '' or str(val).strip() == '-'
    if is_no_artnr(article_number):
        items_same_type = [i for i in all_items if norm(i.asset.name) == key_name and is_no_artnr(i.asset.article_number)]
    else:
        items_same_type = [i for i in all_items if norm(i.asset.name) == key_name and norm(i.asset.article_number) == key_artnr]
    print("DEBUG [GROUP] items_same_type (ID, Status):", [(i.id, i.status) for i in items_same_type])
    if not items_same_type:
        flash('Keine passenden Assets für diese Gruppe gefunden!', 'danger')
        return redirect(url_for('main.inventory_planning_detail', id=session.id))
    item = items_same_type[0]
    if request.method == 'POST':
        counted_quantity_grouped = request.form.get('counted_quantity_grouped', type=int) or 0
        damaged_quantity_grouped = request.form.get('damaged_quantity_grouped', type=int) or 0
        for idx, i in enumerate(items_same_type):
            if idx < counted_quantity_grouped:
                if idx < damaged_quantity_grouped:
                    i.status = 'damaged'
                    i.condition = 'damaged'
                else:
                    i.status = 'found'
                    i.condition = 'good'
                i.counted_quantity = 1
            else:
                i.status = 'missing'
                i.condition = 'missing'
                i.counted_quantity = 0
        db.session.commit()
        flash('Alle Mengen für diese Gruppe wurden gespeichert.', 'success')
        return redirect(url_for('main.inventory_planning_detail', id=session.id))
    # Übergabe der beiden Mengen an das Template (temporär, falls nicht im Modell)
    for i in items_same_type:
        i.counted_quantity1 = getattr(i, 'counted_quantity1', None)
        i.counted_quantity2 = getattr(i, 'counted_quantity2', None)
    return render_template('inventory/check_item.html',
                         item=item,
                         items_same_type=items_same_type,
                         session=session)

@main.route('/inventory/check/item/<int:id>', methods=['GET', 'POST'])

def inventory_item_detail(id):
    """Zeigt und verarbeitet die Detailansicht eines Inventur-Items"""
    item = InventoryItem.query.get_or_404(id)
    
    if request.method == 'POST':
        item.counted_quantity = request.form.get('counted_quantity', type=int)
        item.actual_location = request.form.get('actual_location')
        item.condition = request.form.get('condition')
        item.condition_notes = request.form.get('condition_notes')
        item.counted_by = getattr(current_user, "username", "anonymous")
        item.counted_at = datetime.utcnow()

        # Speichere die Zustände pro Seriennummer als JSON-Liste
        serial_statuses = []
        for serial in request.form.getlist('serial_numbers'):
            status = request.form.get(f'status_{serial}')
            if serial and status:
                serial_statuses.append({'serial_number': serial, 'status': status})
        item.serial_statuses = serial_statuses
        
        # Location korrekt?
        item.location_correct = (item.actual_location.lower() == item.expected_location.lower()) if item.actual_location and item.expected_location else False
        
        # Status basierend auf den Eingaben setzen (mindestens einer damaged/repair_needed → damaged; sonst found)
        if item.counted_quantity == 0:
            item.status = 'missing'
        elif any(s['status'] in ['damaged', 'repair_needed'] for s in serial_statuses):
            item.status = 'damaged'
        else:
            item.status = 'found'
            
        # Bild verarbeiten wenn hochgeladen
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                item.image_path = filename
        
        db.session.commit()
        flash('Asset wurde erfolgreich erfasst!', 'success')
        return redirect(url_for('main.inventory_planning_detail', id=item.session_id))
    
    # Seriennummern wie in der Planung-Ansicht aggregieren
    serial_numbers = [
        i.asset.serial_number
        for i in InventoryItem.query.filter_by(session_id=item.session_id).all()
        if i.asset and i.asset.name == item.asset.name and i.asset.serial_number
    ]

    # serial_statuses als Dict für das Template bereitstellen
    serial_statuses_dict = {}
    if item.serial_statuses:
        for entry in item.serial_statuses:
            serial_statuses_dict[entry['serial_number']] = entry['status']
    return render_template('inventory/item_detail.html', item=item, serial_numbers=serial_numbers, serial_statuses=serial_statuses_dict)


@main.route('/inventory/search', methods=['GET'])

def inventory_search():
    """Suche nach Assets in der Inventur"""
    query = request.args.get('q', '')
    
    if query:
        # Suche in Assets und InventoryItems
        items = (InventoryItem.query
                .join(Asset)
                .filter(or_(
                    Asset.name.ilike(f'%{query}%'),
                    Asset.serial_number.ilike(f'%{query}%'),
                    Asset.category.ilike(f'%{query}%')
                ))
                .all())
    else:
        items = []
    
    return render_template('inventory/search_results.html',
                         items=items,
                         query=query)

@main.route('/inventory/complete/<int:id>', methods=['POST'])
def complete_inventory(id):
    """Schließt eine Inventur ab"""
    session = InventorySession.query.get_or_404(id)
    
    # Prüfe pro Asset nur das Item mit der höchsten gezählten Menge
    from sqlalchemy import func, and_
    subq = db.session.query(
        InventoryItem.asset_id,
        func.max(InventoryItem.counted_quantity).label('max_counted')
    ).filter(
        InventoryItem.session_id == id
    ).group_by(InventoryItem.asset_id).subquery()

    uncounted_items = db.session.query(InventoryItem).join(
        subq,
        and_(
            InventoryItem.asset_id == subq.c.asset_id,
            InventoryItem.counted_quantity == subq.c.max_counted
        )
    ).filter(
        InventoryItem.counted_quantity == None
    ).count()
    if uncounted_items > 0:
        flash(f'Es gibt noch {uncounted_items} ungezählte Assets in dieser Inventur.', 'warning')
        return redirect(url_for('main.inventory_planning_detail', id=id))
    
    # Setze Status für alle Items
    for item in session.items:
        if item.counted_quantity is not None:
            # Prüfe Zustand
            if (item.condition is not None and (item.condition == 'damaged' or item.condition == 'repair_needed')):
                item.status = 'damaged'
            else:
                item.status = 'found'
        else:
            item.status = 'missing'

        # Standortprüfung
        if item.actual_location and item.expected_location:
            item.location_correct = (item.actual_location == item.expected_location)

    # Setze Status auf completed
    session.status = 'completed'
    session.end_date = datetime.utcnow()
    db.session.commit()
    
    flash('Inventur wurde erfolgreich abgeschlossen!', 'success')
    return redirect(url_for('main.inventory_reports'))

@main.route('/uploads/<filename>')
def uploaded_file(filename):
    """Zeigt ein hochgeladenes Bild an"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@main.route('/inventory/planning/add_items/<int:id>', methods=['GET', 'POST'])

def inventory_planning_add_items(id):
    """Fügt Assets zu einer Inventur hinzu"""
    session = InventorySession.query.get_or_404(id)
    
    if request.method == 'POST':
        asset_ids = request.form.getlist('assets')
        for asset_id in asset_ids:
            qty_field = f"expected_quantity_{asset_id}"
            try:
                expected_quantity = int(request.form.get(qty_field, 1))
            except ValueError:
                expected_quantity = 1
            # Prüfen wie viele Items es schon gibt
            existing_items = InventoryItem.query.filter_by(session_id=id, asset_id=asset_id).count()
            # Lege so viele neue Items an, dass insgesamt expected_quantity erreicht wird
            for _ in range(existing_items, expected_quantity):
                item = InventoryItem(
                    session_id=id,
                    asset_id=asset_id,
                    status='pending',
                    expected_quantity=1
                )
                db.session.add(item)
        
        db.session.commit()
        flash('Assets wurden zur Inventur hinzugefügt.', 'success')
        return redirect(url_for('main.inventory_planning_detail', id=id))
    
    # Alle Assets holen, die noch nicht in der Inventur sind
    existing_asset_ids = [item.asset_id for item in session.items]
    available_assets = Asset.query.filter(~Asset.id.in_(existing_asset_ids)).all()
    
    return render_template('inventory/add_items.html',
                         session=session,
                         assets=available_assets)

from sqlalchemy.orm import joinedload

@main.route('/inventory/reports')

def inventory_reports():
    """Zeigt eine Übersicht aller abgeschlossenen Inventuren mit Berichten"""
    completed_sessions = (
        InventorySession.query
        .options(joinedload(InventorySession.items))
        .filter_by(status='completed')
        .order_by(InventorySession.end_date.desc())
        .all()
    )
    # Zusammenfassung nach Typ-Summen-Logik
    session_summaries = {}
    for session in completed_sessions:
        # Aggregiere pro Typ (Name + Artikelnummer)
        type_groups = {}
        damaged = 0
        for item in session.items:
            key = (item.asset.name, item.asset.article_number or "-")
            if key not in type_groups:
                type_groups[key] = {"expected": 0, "counted": 0, "damaged": 0}
            type_groups[key]["expected"] += item.expected_quantity or 0
            type_groups[key]["counted"] += item.counted_quantity or 0
            if item.status == 'damaged':
                type_groups[key]["damaged"] += 1
                damaged += 1
        found = 0
        missing = 0
        total = 0
        for stats in type_groups.values():
            expected_sum = stats["expected"]
            counted_sum = stats["counted"]
            total += expected_sum  # Nur die Typ-Summe zählt!
            if counted_sum >= expected_sum and expected_sum > 0:
                found += expected_sum
            else:
                found += counted_sum if counted_sum > 0 else 0
                missing += expected_sum - counted_sum if expected_sum > counted_sum else 0
        session_summaries[session.id] = {
            'found': found,
            'missing': missing,
            'damaged': damaged,
            'total': total  # Nur die Typ-Summe, nicht die Einzel-Items!
        }

    return render_template('inventory/reports.html', completed_sessions=completed_sessions, session_summaries=session_summaries)


@main.route('/inventory/reports/<int:id>')

def inventory_report_detail(id):
    """Zeigt detaillierte Informationen zu einer abgeschlossenen Inventur"""
    session = InventorySession.query.get_or_404(id)
    if session.status != 'completed':
        flash('Diese Inventur ist noch nicht abgeschlossen.', 'warning')
        return redirect(url_for('main.inventory_reports'))
    # Gruppierung nach Asset-Name und Artikelnummer
    from collections import defaultdict
    asset_groups = defaultdict(lambda: {"name": "", "article_number": "", "expected": 0, "counted": 0, "diff": 0})
    # Aggregiere pro Asset-ID die höchste gezählte Menge (counted_quantity) und die Summe der expected_quantity
    from collections import defaultdict
    # Einzel-Asset-Zusammenfassung (statt pro Typ)
    found = sum(1 for item in session.items if item.status == 'found')
    missing = sum(1 for item in session.items if item.status == 'missing')
    damaged = sum(1 for item in session.items if item.status == 'damaged')
    total = len(session.items)
    summary = {'found': found, 'missing': missing, 'damaged': damaged, 'total': total}

    # DEBUG-Ausgabe: Welche Items werden gezählt?
    print('--- DEBUG für Bericht ---')
    for item in session.items:
        print(f'ID: {item.id}, Asset: {item.asset.name}, Status: {item.status}, counted_quantity: {item.counted_quantity}')
    print(f"Summary: found={summary['found']}, missing={summary['missing']}, damaged={summary['damaged']}, total={summary['total']}")
    print('--- ENDE DEBUG Bericht ---')

    # Aggregiere pro Typ für die Tabellenansicht
    type_stats = {}
    for item in session.items:
        key = (item.asset.name, item.asset.article_number or "-")
        if key not in type_stats:
            type_stats[key] = {"expected": 0, "counted": 0, "damaged": False}
        type_stats[key]["expected"] += item.expected_quantity or 0
        type_stats[key]["counted"] += item.counted_quantity if item.counted_quantity is not None else 0
        if item.status == 'damaged':
            type_stats[key]["damaged"] = True
    # Mappe Typen auf ihren Status
    type_status = {}
    for key, stats in type_stats.items():
        if stats["damaged"]:
            type_status[key] = 'damaged'
        elif stats["counted"] >= stats["expected"] and stats["expected"] > 0:
            type_status[key] = 'found'
        else:
            type_status[key] = 'missing'

    # Gruppiere nach Gerätetyp (Name + Artikelnummer) und berechne Typ-Status
    from collections import defaultdict
    type_stats = {}
    for item in session.items:
        key = (item.asset.name, item.asset.article_number or "-")
        if key not in type_stats:
            type_stats[key] = {"expected": 0, "counted": 0, "damaged": False}
        type_stats[key]["expected"] += item.expected_quantity or 0
        type_stats[key]["counted"] += item.counted_quantity if item.counted_quantity is not None else 0
        if item.status == 'damaged':
            type_stats[key]["damaged"] = True
    # Mappe Typen auf ihren Status
    type_status = {}
    for key, stats in type_stats.items():
        if stats["damaged"]:
            type_status[key] = 'damaged'
        elif stats["counted"] >= stats["expected"] and stats["expected"] > 0:
            type_status[key] = 'found'
        else:
            type_status[key] = 'missing'
    # Erzeuge Asset-Liste mit dynamisch berechnetem Status
    asset_list = []
    for item in session.items:
        key = (item.asset.name, item.asset.article_number or "-")
        dyn_status = type_status[key]
        stats = type_stats[key]
        asset_list.append({
            "item": item,
            "dyn_status": dyn_status,
            "expected": stats["expected"],
            "counted": stats["counted"],
            "diff": stats["counted"] - stats["expected"]
        })
    # Aggregierte Liste pro Asset-Typ für die Übersichtstabelle
    asset_type_list = []
    for key, stats in type_stats.items():
        name, article_number = key
        dyn_status = type_status[key]
        asset_type_list.append({
            "name": name,
            "article_number": article_number,
            "dyn_status": dyn_status,
            "expected": stats["expected"],
            "counted": stats["counted"],
            "diff": stats["counted"] - stats["expected"]
        })
        # Zeitverlauf: Zählungen pro Tag
    from collections import Counter
    import datetime
    timeline_counter = Counter()
    for item in session.items:
        if item.counted_at:
            day = item.counted_at.strftime('%Y-%m-%d')
            timeline_counter[day] += 1
    timeline_labels = sorted(timeline_counter.keys())
    timeline_data = [timeline_counter[day] for day in timeline_labels]

    # Kategorien-Übersicht: Anzahl pro Kategorie
    category_counter = Counter()
    for item in session.items:
        cat = getattr(item.asset, 'category', 'Unbekannt') or 'Unbekannt'
        # Falls cat ein Objekt ist, nutze den Namen
        if hasattr(cat, 'name'):
            cat_label = cat.name
        else:
            cat_label = str(cat)
        category_counter[cat_label] += 1
    category_labels = list(category_counter.keys())
    category_counts = [category_counter[cat] for cat in category_labels]

    return render_template(
        'inventory/report_detail.html',
        session=session,
        asset_list=asset_list,
        summary=summary,
        asset_type_list=asset_type_list,
        timeline_labels=timeline_labels,
        timeline_data=timeline_data,
        category_labels=category_labels,
        category_counts=category_counts
    )



@main.route('/inventory/reports/<int:id>/export')

def inventory_report_export(id):
    """Exportiert einen Inventurbericht als PDF"""
    session = InventorySession.query.get_or_404(id)
    if session.status != 'completed':
        flash('Diese Inventur ist noch nicht abgeschlossen.', 'warning')
        return redirect(url_for('main.inventory_reports'))
    
    # Erstelle ein temporäres PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
        # PDF Dokument erstellen
        doc = SimpleDocTemplate(
            pdf_file.name,
            pagesize=A4,
            rightMargin=2.5*cm,
            leftMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Story (Inhaltselemente)
        story = []
        
        # Titel
        story.append(Paragraph('Inventurbericht', title_style))
        story.append(Paragraph(f'Erstellt am {datetime.now().strftime("%d.%m.%Y")}', normal_style))
        story.append(Spacer(1, 20))
        
        # Allgemeine Informationen
        story.append(Paragraph('Allgemeine Informationen', heading_style))
        info_data = [
            ['Name der Inventur:', session.name],
            ['Standort:', session.location],
            ['Zeitraum:', f'{session.start_date.strftime("%d.%m.%Y")} - {session.end_date.strftime("%d.%m.%Y")}'],
            ['Status:', session.status]
        ]
        info_table = Table(info_data, colWidths=[4*cm, 12*cm])
        info_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Zusammenfassung
        story.append(Paragraph('Zusammenfassung', heading_style))
        total = len(session.items)
        found = sum(1 for item in session.items if item.status == 'found')
        missing = sum(1 for item in session.items if item.status == 'missing')
        damaged = sum(1 for item in session.items if item.status == 'damaged')
        
        summary_data = [
            ['Gesamtanzahl Assets:', str(total)],
            ['Gefunden:', f'{found} ({found/total*100:.1f}%)'],
            ['Fehlend:', f'{missing} ({missing/total*100:.1f}%)'],
            ['Beschädigt:', f'{damaged} ({damaged/total*100:.1f}%)']
        ]
        summary_table = Table(summary_data, colWidths=[4*cm, 12*cm])
        summary_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Asset Liste
        story.append(Paragraph('Detaillierte Asset-Liste', heading_style))
        # Tabellen-Header
        asset_data = [['Asset', 'Status', 'Erfasst am', 'Aktueller Standort', 'Zustand']]
        # Tabellen-Daten
        for item in session.items:
            status_text = {
                'found': 'Gefunden',
                'missing': 'Fehlend',
                'damaged': 'Beschädigt'
            }.get(item.status, item.status)
            
            asset_data.append([
                item.asset.name,
                status_text,
                item.counted_at.strftime('%d.%m.%Y %H:%M') if item.counted_at else '-',
                item.actual_location or '-',
                item.condition or '-'
            ])
        
        # Tabelle erstellen
        asset_table = Table(asset_data, repeatRows=1)
        asset_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(asset_table)
        story.append(Spacer(1, 30))
        
        # Unterschriftszeilen
        signature_data = [[
            Paragraph('____________________<br/>Unterschrift Inventurleiter', normal_style),
            Paragraph('____________________<br/>Unterschrift Prüfer', normal_style)
        ]]
        signature_table = Table(signature_data, colWidths=[8*cm, 8*cm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(signature_table)
        
        # PDF generieren
        doc.build(story)
        
        # PDF-Datei senden
        response = send_file(
            pdf_file.name,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Inventurbericht_{session.name}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
        # Eine Funktion definieren, die die temporäre Datei nach dem Senden löscht
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(pdf_file.name)
            except (OSError, PermissionError):
                pass  # Ignoriere Fehler beim Löschen
        
        return response

@main.route('/inventory/history')

def inventory_history():
    """Zeigt die Historie aller Inventuren"""
    sessions = InventorySession.query.order_by(InventorySession.start_date.desc()).all()
    return render_template('inventory/history.html', sessions=sessions)
