from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, current_app as app
from .models import Assignment
from . import db
from werkzeug.utils import secure_filename
from . import db
from .models import Asset, Assignment, Manufacturer, Supplier, Category, Location
from .forms import AssetForm
from datetime import datetime
import os
import json
from .aftership_tracking import get_all_trackings

def init_app(app):
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('main.md3_assets'))
        else:
            return redirect(url_for('auth.login', md3=1))
        
    # Dashboard route entfernt - wird von main.py behandelt
    
    @app.route('/preview/md3')
    def md3_preview():
        """Vorschau der Material Design 3 Navigation"""
        return render_template('material_preview.html')
    
    @app.route('/preview/navrail')
    def navrail_preview():
        """Vorschau der Material Design 3 Navigation Rail"""
        return render_template('material_navrail_preview.html')
    
    @app.route('/calendar')
    def calendar():
        """Material Design 3 Kalender"""
        return render_template('md3/layouts/calendar.html')
        
    @app.route('/calendar-test')
    def calendar_test():
        """Material Design 3 Kalender (Testversion)"""
        return render_template('md3/layouts/calendar_test.html')
        
    @app.route('/calendar-standalone')
    def calendar_standalone():
        """Standalone Kalender ohne base-Template für Debug"""
        return render_template('md3/layouts/calendar_standalone.html')
        
    @app.route('/calendar-extreme')
    def calendar_extreme():
        """Kalender mit extremen CSS-Überschreibungen für Debug"""
        return render_template('md3/layouts/calendar_base_override.html')
        
    @app.route('/calendar-simple')
    def calendar_simple():
        """Eigenständige Kalender-Seite ohne base.html-Abhängigkeit"""
        return render_template('md3/layouts/calendar_simple.html')
        
    @app.route('/calendar-hybrid')
    def calendar_hybrid():
        """Hybrid-Kalender-Seite mit Navigation, aber ohne base.html-Abhängigkeit"""
        return render_template('md3/layouts/calendar_hybrid.html')
        
    @app.route('/md3/assets')
    def md3_assets():
        """Asset-Übersicht mit Material Design 3"""
        # Dieselbe Logik wie bei der normalen Assets-Route verwenden
        # Filterparameter aus der Anfrage abrufen
        name = request.args.get('name', '')
        category = request.args.get('category', '')
        location = request.args.get('location', '')
        manufacturer = request.args.get('manufacturer', '')
        supplier = request.args.get('supplier', '')
        assignment = request.args.get('assignment', '')
        with_image = request.args.get('with_image') == 'true'
        status = request.args.get('status', 'active')  # Standard: aktive Assets
        group_duplicates = request.args.get('group_duplicates') == 'true'
        
        # Query aufbauen
        query = Asset.query
        
        # Basis-Filter für Name
        if name:
            query = query.filter(Asset.name.ilike(f'%{name}%'))
        
        # Filter für Kategorie
        if category:
            query = query.join(Asset.category).filter(Category.name.ilike(f'%{category}%'))
        
        # Filter für Standort
        if location:
            query = query.join(Asset.location_obj).filter(Location.name.ilike(f'%{location}%'))
        
        # Filter für Hersteller
        if manufacturer:
            query = query.join(Asset.manufacturers).filter(Manufacturer.name.ilike(f'%{manufacturer}%'))
        
        # Filter für Lieferant
        if supplier:
            query = query.join(Asset.suppliers).filter(Supplier.name.ilike(f'%{supplier}%'))
        
        # Filter für Zuordnung
        if assignment:
            query = query.join(Asset.assignments).filter(Assignment.name.ilike(f'%{assignment}%'))
        
        # Filter für Bilder
        if with_image:
            query = query.filter(Asset.image_url.isnot(None))
        
        # Filter für Status
        if status != 'all':
            query = query.filter(Asset.status == status)
        
        # Assets mit allen Filtern abfragen
        assets = query.all()
        
        # Gruppierung von Duplikaten
        if group_duplicates:
            from collections import defaultdict
            # Gruppieren nach Name und Artikelnummer
            grouped_assets = defaultdict(list)
            for asset in assets:
                group_key = (asset.name, asset.article_number)
                grouped_assets[group_key].append(asset)
            
            # Neue Asset-Liste erstellen mit gruppierten Elementen
            result_assets = []
            for key, group in grouped_assets.items():
                if len(group) > 1:
                    # Repräsentatives Asset für die Gruppe auswählen
                    representative = group[0]
                    representative.is_group = True
                    representative.group_count = len(group)
                    representative.group_ids = [a.id for a in group]
                    representative.group_assets = group  # Alle Assets der Gruppe für Details
                    result_assets.append(representative)
                else:
                    # Einzelnes Asset
                    group[0].is_group = False
                    result_assets.append(group[0])
        else:
            # Keine Gruppierung, normale Anzeige
            result_assets = assets
            for asset in result_assets:
                asset.is_group = False
        
        # Ausgewählte Filter für Template
        selected = {
            'name': name,
            'category': category,
            'location': location, 
            'manufacturer': manufacturer,
            'supplier': supplier,
            'assignment': assignment,
            'with_image': with_image,
            'status': status
        }
        
        # CSRF Token für Template bereitstellen
        from flask_wtf.csrf import generate_csrf
        
        # Dropdown-Daten für Asset-Modal bereitstellen
        from .models import Assignment, Manufacturer, Supplier, Category, Location
        categories = Category.query.order_by(Category.name).all()
        manufacturers = Manufacturer.query.order_by(Manufacturer.name).all()
        suppliers = Supplier.query.order_by(Supplier.name).all()
        assignments = Assignment.query.order_by(Assignment.name).all()
        locations = Location.query.order_by(Location.name).all()
        
        from flask import make_response
        
        response = make_response(render_template('md3/layouts/assets.html', 
                              assets=result_assets, 
                              selected=selected, 
                              group_duplicates=group_duplicates,
                              categories=categories,
                              manufacturers=manufacturers,
                              suppliers=suppliers,
                              assignments=assignments,
                              locations=locations,
                              csrf_token=generate_csrf))
        
        # Cache-busting Headers hinzufügen für MD3 Assets
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/api/dropdown-data')
    def api_dropdown_data():
        """API Endpoint für aktuelle Dropdown-Daten"""
        from .models import Assignment, Manufacturer, Supplier, Category, Location
        
        data = {
            'categories': [{'id': c.id, 'name': c.name} for c in Category.query.order_by(Category.name).all()],
            'manufacturers': [{'id': m.id, 'name': m.name} for m in Manufacturer.query.order_by(Manufacturer.name).all()],
            'suppliers': [{'id': s.id, 'name': s.name} for s in Supplier.query.order_by(Supplier.name).all()],
            'assignments': [{'id': a.id, 'name': a.name} for a in Assignment.query.order_by(Assignment.name).all()],
            'locations': [{'id': l.id, 'name': l.name} for l in Location.query.order_by(Location.name).all()]
        }
        
        return jsonify(data)

    @app.route('/assets')
    def assets():
        assets = Asset.query.all()
        return render_template('assets.html', assets=assets)
    
    @app.route('/api/assets', methods=['GET'])
    def api_assets():
        """API endpoint to get assets list for dynamic refresh"""
        try:
            # Get query parameters for filtering
            page = request.args.get('page', 1, type=int)
            per_page = 50  # Assets per page
            category = request.args.get('category', '')
            status = request.args.get('status', '')
            search = request.args.get('search', '')
            
            # Build query
            query = Asset.query
            
            # Apply filters
            if category:
                query = query.filter(Asset.category.like(f'%{category}%'))
            if status:
                query = query.filter(Asset.status.like(f'%{status}%'))
            if search:
                query = query.filter(
                    db.or_(
                        Asset.name.like(f'%{search}%'),
                        Asset.asset_id.like(f'%{search}%'),
                        Asset.artikelnummer.like(f'%{search}%'),
                        Asset.hersteller.like(f'%{search}%')
                    )
                )
            
            # Paginate
            pagination = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # Convert assets to JSON
            assets_data = []
            for asset in pagination.items:
                assets_data.append({
                    'id': asset.id,
                    'asset_id': asset.asset_id,
                    'name': asset.name,
                    'artikelnummer': asset.artikelnummer,
                    'category': str(asset.category) if asset.category else None,
                    'ean': asset.ean,
                    'start': asset.start,
                    'hersteller': asset.hersteller,
                    'serialnumber': asset.serialnumber,
                    'lieferant': asset.lieferant,
                    'created_at': asset.created_at.isoformat() if asset.created_at else None,
                    'updated_at': asset.updated_at.isoformat() if asset.updated_at else None,
                    'status': asset.status,
                    'aktionen': asset.aktionen
                })
            
            return jsonify({
                'success': True,
                'assets': assets_data,
                'pagination': {
                    'page': pagination.page,
                    'pages': pagination.pages,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Fehler beim Laden der Assets: {str(e)}'
            }), 500

    @app.route('/assets/add', methods=['GET', 'POST'])
    def add_asset():
        form = AssetForm()
        form.update_choices()  # Aktualisiere Dropdown-Optionen
        if form.validate_on_submit():
            # Bild speichern, wenn eins hochgeladen wurde
            image_path = None
            if form.image.data:
                filename = secure_filename(form.image.data.filename)
                # Eindeutigen Dateinamen generieren
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'{timestamp}_{filename}'
                # Pfad zum Speichern
                upload_path = os.path.join(app.static_folder, 'uploads')
                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)
                file_path = os.path.join(upload_path, filename)
                form.image.data.save(file_path)
                image_path = f'/static/uploads/{filename}'

            asset = Asset(
                name=form.name.data,
                description=form.description.data,
                image_url=image_path,
                article_number=form.article_number.data,
                category_id=int(form.category.data),
                ean=form.ean.data,
                value=form.value.data,
                status=form.status.data,
                location=form.location.data,
                serial_number=form.serial_number.data,
                purchase_date=form.purchase_date.data
            )
            # Zuordnungen hinzufügen
            if form.assignments.data:
                for assignment_id in form.assignments.data:
                    assignment = Assignment.query.get(assignment_id)
                    if assignment:
                        asset.assignments.append(assignment)
            
            # Hersteller hinzufügen
            if form.manufacturers.data:
                for manufacturer_id in form.manufacturers.data:
                    manufacturer = Manufacturer.query.get(manufacturer_id)
                    if manufacturer:
                        asset.manufacturers.append(manufacturer)
            
            # Lieferanten hinzufügen
            if form.suppliers.data:
                for supplier_id in form.suppliers.data:
                    supplier = Supplier.query.get(supplier_id)
                    if supplier:
                        asset.suppliers.append(supplier)

            db.session.add(asset)
            db.session.commit()
            flash('Asset erfolgreich erstellt.', 'success')
            return redirect(url_for('main.assets'))
        return render_template('edit_asset.html', form=form, is_new=True)

    @app.route('/assets/<int:id>/edit', methods=['GET', 'POST'])
    def edit_asset(id):
        from .forms import DocumentForm
        from .models import Document
        asset = Asset.query.get_or_404(id)
        form = AssetForm(obj=asset)
        doc_form = DocumentForm()
        if form.validate_on_submit():
            # Bild aktualisieren, wenn ein neues hochgeladen wurde
            if form.image.data:
                # Altes Bild löschen, wenn es existiert
                if asset.image_url:
                    old_file = os.path.join(app.root_path, 'static', asset.image_url.lstrip('/static/'))
                    if os.path.exists(old_file):
                        os.remove(old_file)
            
                filename = secure_filename(form.image.data.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'{timestamp}_{filename}'
                upload_path = os.path.join(app.static_folder, 'uploads')
                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)
                asset.image_url = os.path.join('static', 'uploads', filename)
                form.image.data.save(os.path.join(upload_path, filename))

            asset.name = form.name.data
            asset.description = form.description.data
            asset.article_number = form.article_number.data
            asset.category_id = int(form.category.data)
            asset.ean = form.ean.data
            asset.value = form.value.data
            asset.status = form.status.data
            asset.location = form.location.data
            asset.serial_number = form.serial_number.data
            asset.purchase_date = form.purchase_date.data

            # Zuordnungen aktualisieren
            asset.assignments = []
            if form.assignments.data:
                for assignment_id in form.assignments.data:
                    assignment = Assignment.query.get(assignment_id)
                    if assignment:
                        asset.assignments.append(assignment)
        
            # Hersteller aktualisieren
            asset.manufacturers = []
            if form.manufacturers.data:
                for manufacturer_id in form.manufacturers.data:
                    manufacturer = Manufacturer.query.get(manufacturer_id)
                    if manufacturer:
                        asset.manufacturers.append(manufacturer)
        
            # Lieferanten aktualisieren
            asset.suppliers = []
            if form.suppliers.data:
                for supplier_id in form.suppliers.data:
                    supplier = Supplier.query.get(supplier_id)
                    if supplier:
                        asset.suppliers.append(supplier)

            db.session.commit()
            flash('Asset erfolgreich aktualisiert.', 'success')
            return redirect(url_for('main.asset_details', id=asset.id))
        
        documents = Document.query.filter_by(asset_id=id).all()
        return render_template('edit_asset.html', form=form, doc_form=doc_form, asset=asset, documents=documents, is_new=False)

    @app.route('/assets/<int:id>')
    def asset_details(id):
        asset = Asset.query.get_or_404(id)
        return render_template('asset_details.html', asset=asset)
    
    @app.route('/api/assets/<int:id>')
    def get_asset_data(id):
        """API endpoint to get asset data for modal editing"""
        asset = Asset.query.get_or_404(id)
        categories = Category.query.order_by(Category.name).all()
        locations = Location.query.order_by(Location.name).all()
        manufacturers = Manufacturer.query.order_by(Manufacturer.name).all()
        suppliers = Supplier.query.order_by(Supplier.name).all()
        assignments = Assignment.query.order_by(Assignment.name).all()
        
        return jsonify({
            'asset': {
                'id': asset.id,
                'name': asset.name,
                'description': asset.description,
                'article_number': asset.article_number,
                'ean': asset.ean,
                'value': float(asset.value) if asset.value else 0.0,
                'status': asset.status,
                'serial_number': asset.serial_number,
                'purchase_date': asset.purchase_date.isoformat() if asset.purchase_date else None,
                'category_id': asset.category_id,
                'location_id': asset.location_id,
                'manufacturer_ids': [m.id for m in asset.manufacturers],
                'supplier_ids': [s.id for s in asset.suppliers],
                'assignment_ids': [a.id for a in asset.assignments],
                'image_url': asset.image_url
            },
            'categories': [{'id': c.id, 'name': c.name} for c in categories],
            'locations': [{'id': l.id, 'name': l.name} for l in locations],
            'manufacturers': [{'id': m.id, 'name': m.name} for m in manufacturers],
            'suppliers': [{'id': s.id, 'name': s.name} for s in suppliers],
            'assignments': [{'id': a.id, 'name': a.name} for a in assignments]
        })
    
    @app.route('/api/assets/<int:id>/update', methods=['POST'])
    def update_asset_api(id):
        """API endpoint to update asset via AJAX"""
        from .models import Document
        asset = Asset.query.get_or_404(id)
        
        try:
            # Update basic fields
            asset.name = request.form.get('name', '').strip()
            asset.description = request.form.get('description', '').strip()
            asset.article_number = request.form.get('article_number', '').strip()
            asset.ean = request.form.get('ean', '').strip()
            asset.serial_number = request.form.get('serial_number', '').strip()
            # Handle status - convert German to English
            status_form = request.form.get('status', 'Aktiv')
            status_mapping = {
                'Aktiv': 'active',
                'Inaktiv': 'inactive',
                'Ausgeliehen': 'on_loan',
                'Defekt': 'defect',
                'Wartung': 'maintenance',
                'Ausgemustert': 'retired',
                'active': 'active',
                'inactive': 'inactive',
                'on_loan': 'on_loan',
                'defect': 'defect',
                'maintenance': 'maintenance',
                'retired': 'retired'
            }
            asset.status = status_mapping.get(status_form, 'active')
            
            # Handle value
            value_str = request.form.get('value', '0')
            try:
                asset.value = float(value_str) if value_str else 0.0
            except ValueError:
                asset.value = 0.0
            
            # Handle purchase_date
            purchase_date_str = request.form.get('purchase_date')
            if purchase_date_str:
                try:
                    asset.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
                except ValueError:
                    asset.purchase_date = None
            else:
                asset.purchase_date = None
            
            # Handle category
            category_id = request.form.get('category_id')
            asset.category_id = int(category_id) if category_id and category_id != '' else None
            
            # Handle location
            location_id = request.form.get('location_id')
            asset.location_id = int(location_id) if location_id and location_id != '' else None
            
            # Handle manufacturers (many-to-many)
            asset.manufacturers = []
            manufacturer_ids = request.form.getlist('manufacturer_ids[]')
            if manufacturer_ids:
                for manufacturer_id in manufacturer_ids:
                    manufacturer = Manufacturer.query.get(manufacturer_id)
                    if manufacturer:
                        asset.manufacturers.append(manufacturer)
            
            # Handle suppliers (many-to-many)
            asset.suppliers = []
            supplier_ids = request.form.getlist('supplier_ids[]')
            if supplier_ids:
                for supplier_id in supplier_ids:
                    supplier = Supplier.query.get(supplier_id)
                    if supplier:
                        asset.suppliers.append(supplier)
            
            # Handle assignments (many-to-many)
            asset.assignments = []
            assignment_ids = request.form.getlist('assignment_ids[]')
            if assignment_ids:
                for assignment_id in assignment_ids:
                    assignment = Assignment.query.get(assignment_id)
                    if assignment:
                        asset.assignments.append(assignment)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Asset erfolgreich aktualisiert',
                'asset': {
                    'id': asset.id,
                    'name': asset.name,
                    'description': asset.description,
                    'value': float(asset.value) if asset.value else 0.0,
                    'category': asset.category.name if asset.category else None,
                    'location': asset.location_obj.name if asset.location_obj else None
                }
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Fehler beim Aktualisieren: {str(e)}'
            }), 500

    @app.route('/assets/<int:id>/qr')
    def asset_qr(id):
        import qrcode
        import io
        asset = Asset.query.get_or_404(id)
        # URL zur Asset-Detailseite
        qr_url = url_for('main.asset_details', id=asset.id, _external=True)
        img = qrcode.make(qr_url)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png', as_attachment=False, download_name=f'asset_{asset.id}_qr.png')

    @app.route('/assets/<int:id>/delete', methods=['POST'])
    def delete_asset(id):
        asset = Asset.query.get_or_404(id)
        db.session.delete(asset)
        db.session.commit()
        flash('Asset erfolgreich gelöscht.', 'success')
        return jsonify({'success': True})

    # API-Routen für Zuordnungen
    @app.route('/api/assignments/create', methods=['POST'])
    def create_assignment():
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
        
        try:
            # Check if assignment already exists
            existing = Assignment.query.filter_by(name=name).first()
            if existing:
                return jsonify({'success': False, 'message': 'Eine Zuordnung mit diesem Namen existiert bereits'}), 400
            
            assignment = Assignment(name=name, description=description if description else None)
            db.session.add(assignment)
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f'Zuordnung "{name}" erfolgreich erstellt',
                'assignment': {
                    'id': assignment.id, 
                    'name': assignment.name,
                    'description': assignment.description
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Fehler beim Erstellen: {str(e)}'}), 500

    @app.route('/api/assignments', methods=['GET'])
    def get_assignments():
        try:
            assignments = Assignment.query.order_by(Assignment.name).all()
            return jsonify({
                'success': True,
                'assignments': [{'id': a.id, 'name': a.name, 'description': a.description} for a in assignments]
            })
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/assignments/add', methods=['POST'])
    def add_assignment():
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
        
        try:
            assignment = Assignment(name=data['name'])
            db.session.add(assignment)
            db.session.commit()
            return jsonify({'success': True, 'assignment': {'id': assignment.id, 'name': assignment.name}})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/md3/locations')
    def md3_locations():
        """MD3 Standorte-Liste"""
        from .models import Location, Asset
        from flask_wtf.csrf import generate_csrf
        from sqlalchemy import func
        
        # Alle Standorte mit Asset-Anzahl laden
        locations_with_counts = db.session.query(
            Location,
            func.count(Asset.id).label('asset_count')
        ).outerjoin(Asset, Location.id == Asset.location_id).group_by(Location.id).all()
        
        # Locations-Objekte mit asset_count Attribut erweitern und zu Dictionaries konvertieren
        locations = []
        locations_dict = []
        for location, asset_count in locations_with_counts:
            # Asset-Anzahl als Attribut hinzufügen
            location.asset_count = asset_count
            locations.append(location)
            
            # Für JavaScript: Location zu Dictionary konvertieren
            location_dict = {
                'id': location.id,
                'name': location.name,
                'street': location.street,
                'postal_code': location.postal_code,
                'city': location.city,
                'state': location.state,
                'size_sqm': location.size_sqm,
                'seats': location.seats,
                'description': location.description,
                'latitude': location.latitude,
                'longitude': location.longitude,
                'google_rating': location.google_rating,
                'google_reviews_count': location.google_reviews_count,
                'google_maps_url': location.google_maps_url,
                'asset_count': asset_count,
                'is_active': location.is_active if hasattr(location, 'is_active') else True,
                'location_type': location.location_type if hasattr(location, 'location_type') else 'Büro',
                'available': location.available if hasattr(location, 'available') else True,
                'image_url': location.image_url if hasattr(location, 'image_url') else None
            }
            locations_dict.append(location_dict)
        
        # CSRF Token für Template bereitstellen
        return render_template('md3/layouts/locations.html', 
                              locations=locations,
                              locations_dict=locations_dict,
                              csrf_token=generate_csrf)
    
    @app.route('/api/locations/<int:location_id>/details')
    def location_details_api(location_id):
        """API für vollständige Location-Details"""
        from .models import Location, Asset, LocationImage
        from sqlalchemy import func
        
        try:
            # Location mit allen Details laden
            location = Location.query.get_or_404(location_id)
            
            # Assets am Standort laden
            assets = Asset.query.filter_by(location_id=location_id).all()
            
            # Galerie-Bilder laden (falls LocationImage Model existiert)
            gallery_images = []
            try:
                gallery_images = LocationImage.query.filter_by(location_id=location_id).all()
            except:
                pass  # LocationImage Model existiert möglicherweise nicht
            
            # Bestand nach Kategorien aggregieren
            from .models import Category
            category_stats = db.session.query(
                Asset.category_id,
                func.count(Asset.id).label('count'),
                func.sum(Asset.value).label('total_value')
            ).filter_by(location_id=location_id).group_by(Asset.category_id).all()
            
            # Response-Daten zusammenstellen
            response_data = {
                'id': location.id,
                'name': location.name,
                'street': getattr(location, 'street', ''),
                'postal_code': getattr(location, 'postal_code', ''),
                'city': getattr(location, 'city', ''),
                'state': getattr(location, 'state', ''),
                'address': getattr(location, 'address', ''),
                'size_sqm': getattr(location, 'size_sqm', None),
                'seats': getattr(location, 'seats', None),
                'description': getattr(location, 'description', ''),
                'location_type': getattr(location, 'location_type', 'Büro'),
                'is_active': getattr(location, 'is_active', True),
                'available': getattr(location, 'available', True),
                'capacity': getattr(location, 'capacity', None),
                'latitude': float(location.latitude) if getattr(location, 'latitude', None) else None,
                'longitude': float(location.longitude) if getattr(location, 'longitude', None) else None,
                'image_url': getattr(location, 'image_url', ''),
                'google_rating': getattr(location, 'google_rating', None),
                'google_reviews_count': getattr(location, 'google_reviews_count', None),
                'google_maps_url': getattr(location, 'google_maps_url', ''),
                'show_reviews': getattr(location, 'show_reviews', True),
                'asset_count': len(assets),
                'assets': [{
                    'id': asset.id,
                    'asset_id': getattr(asset, 'asset_id', ''),
                    'name': asset.name,
                    'category': asset.category.name if asset.category else 'Unbekannt',
                    'value': float(asset.value) if asset.value else 0,
                    'status': getattr(asset, 'status', 'Aktiv')
                } for asset in assets],
                'gallery_images': [{
                    'id': img.id,
                    'filename': getattr(img, 'filename', ''),
                    'description': getattr(img, 'description', ''),
                    'comment': getattr(img, 'comment', ''),
                    'mimetype': getattr(img, 'mimetype', ''),
                    'uploader': getattr(img, 'uploader', ''),
                    'upload_date': img.upload_date.isoformat() if getattr(img, 'upload_date', None) else None
                } for img in gallery_images],
                'category_stats': [{
                    'category_id': stat.category_id,
                    'category_name': Category.query.get(stat.category_id).name if stat.category_id and Category.query.get(stat.category_id) else 'Unbekannt',
                    'count': stat.count,
                    'total_value': float(stat.total_value) if stat.total_value else 0
                } for stat in category_stats]
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/locations/<int:location_id>/reviews')
    def location_reviews_api(location_id):
        """API für Google Reviews eines Standorts"""
        from .models import Location
        
        try:
            location = Location.query.get_or_404(location_id)
            
            # TODO: Integrate with real Google Places API
            # For now, return mock data for demonstration
            mock_reviews = [
                {
                    'author_name': 'Max Mustermann',
                    'rating': 5,
                    'text': 'Hervorragender Standort mit toller Atmosphäre und professionellem Service. Sehr zu empfehlen!',
                    'time': '2 Wochen her',
                    'profile_photo_url': None
                },
                {
                    'author_name': 'Anna Schmidt',
                    'rating': 4,
                    'text': 'Sehr gute Lage und moderne Ausstattung. Das Team ist freundlich und hilfsbereit.',
                    'time': '1 Monat her',
                    'profile_photo_url': None
                },
                {
                    'author_name': 'Thomas Weber',
                    'rating': 5,
                    'text': 'Top Standort! Perfekte Infrastruktur und zentrale Lage. Immer wieder gerne.',
                    'time': '3 Monate her',
                    'profile_photo_url': None
                }
            ]
            
            response_data = {
                'success': True,
                'has_reviews': True,  # Set to False if no Google reviews available
                'reviews': mock_reviews,
                'description': location.description or '',
                'message': 'Mock-Daten (Google Places API noch nicht konfiguriert)'
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/assignments/delete', methods=['POST'])
    def delete_assignment():
        data = request.get_json()
        assignment_id = data.get('id')
        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'success': False, 'message': 'Zuordnung nicht gefunden'}), 404
        
        db.session.delete(assignment)
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400


    # API-Routen für Hersteller
    @app.route('/manufacturers/add', methods=['POST'])
    def add_manufacturer():
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
        
        manufacturer = Manufacturer(
            name=data['name'],
            description=data.get('description', ''),
            website=data.get('website', ''),
            contact_info=data.get('contact_info', '')
        )
        db.session.add(manufacturer)
        try:
            db.session.commit()
            return jsonify({'success': True, 'id': manufacturer.id, 'name': manufacturer.name})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400


    @app.route('/manufacturers/delete', methods=['POST'])
    def delete_manufacturer():
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
        
        manufacturer = Manufacturer.query.filter_by(name=data['name']).first()
        if not manufacturer:
            return jsonify({'success': False, 'message': 'Hersteller nicht gefunden'}), 404
        
        db.session.delete(manufacturer)
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400


    # API-Routen für Lieferanten
    @app.route('/suppliers/add', methods=['POST'])
    def add_supplier():
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
        
        supplier = Supplier(
            name=data['name'],
            description=data.get('description', ''),
            website=data.get('website', ''),
            contact_info=data.get('contact_info', '')
        )
        db.session.add(supplier)
        try:
            db.session.commit()
            return jsonify({'success': True, 'id': supplier.id, 'name': supplier.name})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400


    @app.route('/suppliers/delete', methods=['POST'])
    def delete_supplier():
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
        
        supplier = Supplier.query.filter_by(name=data['name']).first()
        if not supplier:
            return jsonify({'success': False, 'message': 'Lieferant nicht gefunden'}), 404
        
        db.session.delete(supplier)
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
    
    
    # API-Routen für Ausleihen
    @app.route('/api/loans/<int:id>')
    def get_loan_data(id):
        """API endpoint to get loan data"""
        from .models import Loan
        loan = Loan.query.get_or_404(id)
        
        return jsonify({
            'loan': {
                'id': loan.id,
                'asset_id': loan.asset_id,
                'borrower_name': loan.borrower_name,
                'start_date': loan.start_date.strftime('%Y-%m-%d') if loan.start_date else None,
                'expected_return_date': loan.expected_return_date.strftime('%Y-%m-%d') if loan.expected_return_date else None,
                'actual_return_date': loan.actual_return_date.strftime('%Y-%m-%d') if loan.actual_return_date else None,
                'notes': loan.notes
            }
        })
