from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, current_app as app
from .models import Assignment
from . import db
from werkzeug.utils import secure_filename
from . import db
from .models import Asset, Assignment, Manufacturer, Supplier, Category
from .forms import AssetForm
from datetime import datetime
import os

def init_app(app):
    @app.route('/')
    def index():
        return redirect(url_for('main.assets'))

    @app.route('/assets')
    def assets():
        assets = Asset.query.all()
        return render_template('assets.html', assets=assets)

            return jsonify({'success': False, 'message': 'Kategorie nicht gefunden'}), 404
        db.session.delete(category)
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400

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

    @app.route('/assignments/delete', methods=['POST'])
    def delete_assignment():
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
        
        assignment = Assignment.query.filter_by(name=data['name']).first()
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
