from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, current_app as app
from .models import Assignment
from . import db
from werkzeug.utils import secure_filename
from . import db
from .models import Asset, Assignment, Manufacturer, Supplier, Category
from .forms import AssetForm
from datetime import datetime
import os
import json
from .aftership_tracking import get_all_trackings

def init_app(app):
    @app.route('/')
    def index():
        return redirect(url_for('main.assets'))
        
    @app.route('/dashboard')
    def dashboard():
        """Dashboard mit MD3 Design"""
        # Tracking-Daten für die Karte abrufen
        try:
            tracking_data = get_all_trackings()
            # Für die Karte relevante Daten als JSON serialisieren
            tracking_json = json.dumps({
                'locations': tracking_data['locations'],
                'counts': tracking_data['counts']
            })
        except Exception as e:
            app.logger.error(f"Fehler beim Abrufen der Tracking-Daten: {e}")
            tracking_json = json.dumps({'locations': [], 'counts': {'in_transit': 0, 'delivered': 0, 'pending': 0, 'total': 0}})
        
        # Hersteller-Auswertung für Dashboard (nur aktive Assets)
        from .models import Manufacturer, Asset
        manufacturer_data = []
        manufacturers = Manufacturer.query.order_by(Manufacturer.name).all()
        for manufacturer in manufacturers:
            count = Asset.query.filter(Asset.manufacturers.any(Manufacturer.id == manufacturer.id), Asset.status == 'active').count()
            manufacturer_data.append({'manufacturer': manufacturer.name, 'count': count})
        # Optional: Nur Hersteller mit mindestens einem Asset anzeigen
        manufacturer_data = [m for m in manufacturer_data if m['count'] > 0]
        
        # Chart-Daten für das Dashboard zusammenstellen
        chart_data = {
            'manufacturer_data': manufacturer_data
        }
        
        return render_template('md3/layouts/dashboard.html', tracking_json=tracking_json, chart_data=chart_data)
    
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
            query = query.filter(Asset.location.ilike(f'%{location}%'))
        
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
        
        return render_template('md3/layouts/assets.html', 
                              assets=result_assets, 
                              selected=selected, 
                              group_duplicates=group_duplicates,
                              csrf_token=generate_csrf)

    @app.route('/assets')
    def assets():
        assets = Asset.query.all()
        return render_template('assets.html', assets=assets)

    @app.route('/assets/add', methods=['GET', 'POST'])
    def add_asset():
        form = AssetForm()
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
        asset = Asset.query.get_or_404(id)
        form = AssetForm(obj=asset)
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
        return render_template('edit_asset.html', form=form, asset=asset, is_new=False)

    @app.route('/assets/<int:id>')
    def asset_details(id):
        asset = Asset.query.get_or_404(id)
        return render_template('asset_details.html', asset=asset)

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
    @app.route('/assignments/add', methods=['POST'])
    def add_assignment():
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
        
        assignment = Assignment(
            name=data['name'],
            description=data.get('description', '')
        )
        db.session.add(assignment)
        try:
            db.session.commit()
            return jsonify({'success': True, 'id': assignment.id, 'name': assignment.name})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
    
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
                'asset_count': asset_count
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
                    'category_name': 'Kategorie ' + str(stat.category_id) if stat.category_id else 'Unbekannt',
                    'count': stat.count,
                    'total_value': float(stat.total_value) if stat.total_value else 0
                } for stat in category_stats]
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

